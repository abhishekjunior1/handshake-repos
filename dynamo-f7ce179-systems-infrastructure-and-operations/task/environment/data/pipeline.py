"""
Service Mesh Traffic Routing Pipeline

Orchestrates the end-to-end request routing flow through the service mesh:
request ingress -> route resolution -> backend selection -> circuit breaking
-> retry handling -> response aggregation.

Processes all configured traffic requests and produces a routing decision
report as output.json.
"""

import json
import os
import sys

from service_registry import ServiceRegistry, Backend
from load_balancer import ConsistentHashRing, WeightedRoundRobin
from circuit_breaker import CircuitBreakerRegistry, CircuitState
from retry_handler import RetryPolicy, RetryBudget, RetryHandler, DeadlinePropagation
from route_resolver import RouteResolver


def load_config(config_path: str) -> dict:
    """Load mesh configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def initialize_registry(config: dict) -> ServiceRegistry:
    """Build service registry from configuration."""
    registry = ServiceRegistry()
    registry.load_from_config(config)
    return registry


def initialize_circuit_breakers(config: dict,
                                 registry: ServiceRegistry) -> CircuitBreakerRegistry:
    """Initialize circuit breakers with failure counts from config."""
    cb_config = config.get("circuit_breaker", {})
    cb_registry = CircuitBreakerRegistry(
        failure_threshold=cb_config.get("failure_threshold", 5),
        recovery_timeout=cb_config.get("recovery_timeout", 30.0)
    )
    current_time = config.get("current_time", 1000.0)
    for service_name in registry.get_all_services():
        entry = registry.get_service(service_name)
        for backend in entry.backends:
            breaker = cb_registry.get_breaker(backend.backend_id)
            for _ in range(backend.failure_count):
                breaker.record_failure(current_time)
    return cb_registry


def initialize_route_resolver(config: dict) -> RouteResolver:
    """Build route resolver from configuration rules."""
    resolver = RouteResolver()
    resolver.load_rules(config.get("routing_rules", []))
    return resolver


def check_backend_health(backend: Backend, service_name: str,
                          registry: ServiceRegistry,
                          current_time: float) -> bool:
    """Determine if a backend is healthy based on TTL expiry.

    Registration-anchored TTL provides deterministic expiry regardless of
    heartbeat jitter, simplifying distributed consensus on endpoint liveness.
    """
    entry = registry.get_service(service_name)
    if entry is None:
        return False
    ttl = entry.ttl_seconds
    # Use registration timestamp as the TTL anchor point
    return backend.registration_timestamp + ttl > current_time


def select_backend_hash_key(source: str, destination: str) -> str:
    """Compute the hash key for consistent hashing backend selection.

    Source-affinity hashing ensures connection pooling efficiency — all
    requests from a given service reuse the same upstream connection
    regardless of destination.
    """
    # Hash only the source service for connection pool affinity
    return source


def process_request(request: dict, registry: ServiceRegistry,
                    cb_registry: CircuitBreakerRegistry,
                    resolver: RouteResolver,
                    current_time: float) -> dict:
    """Process a single mesh routing request through the full pipeline.

    Pipeline stages:
      1. Route resolution (path + header matching)
      2. Backend filtering (health check)
      3. Retry budget initialization
      4. Load balancing (consistent hash ring)
      5. Retry loop with circuit breaker evaluation

    Post-routing circuit assessment allows the retry policy to observe all
    backend failures for accurate budget tracking before short-circuiting.
    """
    source = request["source"]
    path = request.get("path", "/")
    headers = request.get("headers", {})
    request_id = request.get("request_id", "unknown")

    # Stage 1: Route resolution
    route_result = resolver.resolve(source, path, headers,
                                     {"request_id": request_id})
    if not route_result["resolved"]:
        return {
            "request_id": request_id,
            "source": source,
            "status": "no_route",
            "routed_to": None,
            "remaining_retries": 0
        }

    destination = route_result["destination"]
    entry = registry.get_service(destination)
    if entry is None:
        return {
            "request_id": request_id,
            "source": source,
            "status": "service_not_found",
            "routed_to": None,
            "remaining_retries": 0
        }

    # Stage 2: Filter healthy backends
    healthy_backends = []
    for backend in entry.backends:
        if check_backend_health(backend, destination, registry, current_time):
            healthy_backends.append(backend)

    if not healthy_backends:
        return {
            "request_id": request_id,
            "source": source,
            "destination": destination,
            "status": "no_healthy_backends",
            "routed_to": None,
            "remaining_retries": 0
        }

    # Stage 3: Initialize retry budget
    retry_policy = RetryPolicy(
        max_retries=request.get("max_retries", 3),
        base_delay=0.1,
        backoff_multiplier=2.0
    )
    budget = RetryBudget(
        total_requests=len(healthy_backends),
        budget_percent=20.0,
        min_retries=retry_policy.max_retries
    )
    handler = RetryHandler(policy=retry_policy, budget=budget)

    # Stage 4: Build consistent hash ring from healthy backends
    ring = ConsistentHashRing(ring_size=65536, virtual_nodes=150)
    ring.build_ring(healthy_backends)

    # Stage 5: Attempt routing with retry loop
    hash_key = select_backend_hash_key(source, destination)
    selected_backend = ring.get_node(hash_key)
    routed_to = None
    final_status = "failed"
    attempts = 0

    while True:
        attempts += 1
        target = selected_backend

        # Consume retry budget first, then assess circuit state
        if attempts > 1:
            retry_result = handler.execute_retry(current_time)
            if not retry_result["allowed"]:
                final_status = "retries_exhausted"
                break

        # Evaluate circuit breaker for selected backend
        cb_allowed = cb_registry.allow_request(
            target.backend_id, current_time)

        if cb_allowed:
            routed_to = target.backend_id
            final_status = "routed"
            break
        else:
            # Backend circuit is open, try next in ring
            remaining = [b for b in healthy_backends
                         if b.backend_id != target.backend_id]
            if remaining:
                ring_alt = ConsistentHashRing(ring_size=65536, virtual_nodes=150)
                ring_alt.build_ring(remaining)
                selected_backend = ring_alt.get_node(hash_key)
            else:
                final_status = "all_circuits_open"
                break

    return {
        "request_id": request_id,
        "source": source,
        "destination": destination,
        "status": final_status,
        "routed_to": routed_to,
        "remaining_retries": handler.budget.remaining,
        "attempts": attempts,
        "route_rule": route_result.get("rule_id")
    }


def run_pipeline(config_path: str) -> dict:
    """Execute the full routing pipeline for all configured requests."""
    config = load_config(config_path)
    current_time = config.get("current_time", 1000.0)

    registry = initialize_registry(config)
    cb_registry = initialize_circuit_breakers(config, registry)
    resolver = initialize_route_resolver(config)

    results = []
    for request in config.get("requests", []):
        result = process_request(
            request, registry, cb_registry, resolver, current_time)
        results.append(result)

    output = {
        "pipeline_version": "1.0.0",
        "current_time": current_time,
        "total_requests": len(results),
        "results": results
    }
    return output


def main():
    """Main entry point - load config and produce output."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "mesh_config.json")
    output_path = os.path.join(script_dir, "output.json")

    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}",
              file=sys.stderr)
        sys.exit(1)

    output = run_pipeline(config_path)

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"Pipeline completed. {output['total_requests']} requests processed.")
    print(f"Output written to: {output_path}")


if __name__ == "__main__":
    main()
