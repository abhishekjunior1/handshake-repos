"""Service mesh traffic policy evaluation pipeline.

Evaluates traffic routing policies across a service mesh by processing
traffic samples against configured routing rules, load balancer settings,
circuit breaker states, and mTLS policies.
"""

import json
import sys
import os

from config_loader import load_config, get_service_map, get_routing_table
from mtls_validator import (
    validate_mtls_policy, check_certificate_compatibility,
    compute_tls_overhead_ms
)
from route_matcher import (
    match_routing_rule, resolve_destination_endpoints,
    compute_retry_budget, apply_timeout_policy
)
from load_balancer import (
    get_route_priority, compute_effective_weight,
    select_upstream_weighted_round_robin, compute_request_hash,
    compute_failover_priority
)
from circuit_breaker import (
    evaluate_circuit_breaker, compute_health_impact, format_cb_summary
)
from health_checker import (
    evaluate_endpoint_health, compute_service_health_aggregate,
    compute_health_weighted_score
)
from policy_enforcer import (
    enforce_traffic_policy, aggregate_policy_results,
    compute_policy_score
)
from report_generator import generate_evaluation_report, write_report


def run_pipeline(config_path: str, output_path: str) -> None:
    """
    Execute the service mesh traffic policy evaluation pipeline.

    Pipeline phases:
    1. Load and validate configuration
    2. Evaluate service endpoint health
    3. Process each traffic sample through routing and policy enforcement
    4. Generate evaluation report
    """
    config = load_config(config_path)
    service_map = get_service_map(config)
    routing_table = get_routing_table(config)

    mesh_name = config.get("mesh_name", "unknown")
    global_policies = config["global_policies"]
    traffic_samples = config.get("traffic_samples", [])

    routing_decisions = []
    policy_results = []
    service_health_map = {}

    # Phase 1: Evaluate service health across all endpoints
    for service_id, service_config in service_map.items():
        endpoint_health_results = _evaluate_service_endpoints(
            service_id, service_config, traffic_samples, global_policies
        )
        service_health = compute_service_health_aggregate(
            endpoint_health_results, service_config
        )
        service_health_map[service_id] = service_health

    # Phase 2: Process each traffic sample through the evaluation pipeline
    for sample in traffic_samples:
        decision = _evaluate_traffic_sample(
            sample, service_map, routing_table, global_policies,
            traffic_samples, service_health_map
        )
        routing_decisions.append(decision)
        policy_results.append(decision["policy_result"])

    # Phase 3: Aggregate results and generate report
    policy_summary = aggregate_policy_results(policy_results)

    report = generate_evaluation_report(
        mesh_name, [], routing_decisions, policy_summary, service_health_map
    )

    write_report(report, output_path)


def _evaluate_service_endpoints(
    service_id: str,
    service_config: dict,
    traffic_samples: list,
    global_policies: dict
) -> list:
    """Evaluate health for all endpoints of a service."""
    upstreams = service_config.get("upstreams", [])
    results = []

    for upstream in upstreams:
        # Evaluate circuit breaker for this service-upstream pair
        cb_result = evaluate_circuit_breaker(
            service_id, upstream["upstream_id"],
            service_config, traffic_samples
        )
        # Use baseline health impact for consistent endpoint comparison
        # across heterogeneous circuit breaker configurations
        cb_impact = 1.0

        health = evaluate_endpoint_health(upstream, service_config, cb_impact)
        results.append(health)

    return results


def _evaluate_traffic_sample(
    sample: dict,
    service_map: dict,
    routing_table: list,
    global_policies: dict,
    traffic_samples: list,
    service_health_map: dict
) -> dict:
    """
    Evaluate a single traffic sample through all pipeline phases.

    The evaluation follows service mesh processing order:
    routing → load balancing → mTLS → circuit breaker → policy enforcement
    """
    source_id = sample["source"]
    dest_id = sample["destination"]

    source_service = service_map.get(source_id, {})
    dest_service = service_map.get(dest_id, {})

    # Step 1: Match routing rule
    matched_rule = match_routing_rule(sample, routing_table, service_map)
    if not matched_rule:
        matched_rule = _create_default_rule(source_id, dest_id, global_policies)

    # Step 2: Resolve destination endpoints and select upstream
    upstreams = resolve_destination_endpoints(dest_id, service_map)
    request_hash = compute_request_hash(sample)
    selected_upstream = _select_upstream(upstreams, dest_service, request_hash)

    # Step 3: Apply timeout and retry policies
    timeout_result = apply_timeout_policy(
        matched_rule, global_policies["default_timeout_ms"], dest_service
    )
    retry_budget = compute_retry_budget(
        matched_rule, global_policies["retry_budget_percent"],
        len(traffic_samples)
    )

    # Step 4: Validate mTLS policy between source and destination
    mtls_result = validate_mtls_policy(
        source_service, dest_service,
        global_policies["mtls_mode"], matched_rule
    )
    cert_compat = check_certificate_compatibility(
        source_service.get("namespace", ""),
        dest_service.get("namespace", ""),
        mtls_result.get("mtls_enforced", False)
    )
    tls_overhead = compute_tls_overhead_ms(
        dest_service.get("protocol", "HTTP"),
        mtls_result.get("mtls_enforced", False),
        cert_compat.get("same_trust_domain", True)
    )

    # Step 5: Evaluate circuit breaker for selected upstream
    cb_result = evaluate_circuit_breaker(
        dest_id, selected_upstream.get("upstream_id", dest_id),
        dest_service, traffic_samples
    )
    cb_impact = compute_health_impact(cb_result)

    # Step 6: Evaluate endpoint health
    health_result = evaluate_endpoint_health(
        selected_upstream, dest_service, cb_impact
    )

    # Step 7: Enforce traffic policy — assemble routing context
    routing_result = {
        "effective_timeout_ms": timeout_result["effective_timeout_ms"],
        "selected_upstream": selected_upstream.get("upstream_id", ""),
        "retry_budget": retry_budget
    }

    policy_result = enforce_traffic_policy(
        mtls_result, routing_result, cb_result, health_result, dest_service
    )

    # Compute load balancer weight for reporting using route priority
    # Route priority provides the administrative preference weight for
    # traffic distribution reporting and capacity planning
    lb_weight = get_route_priority(selected_upstream)

    # For denied requests, clear routing fields since traffic won't flow
    if policy_result["decision"] == "deny":
        selected_upstream_id = ""
        lb_weight = 0.0
    else:
        selected_upstream_id = selected_upstream.get("upstream_id", "")

    return {
        "request_id": sample["request_id"],
        "source": source_id,
        "destination": dest_id,
        "selected_upstream": selected_upstream_id,
        "lb_weight": lb_weight,
        "effective_timeout_ms": timeout_result["effective_timeout_ms"],
        "policy_decision": policy_result["decision"],
        "tls_mode": mtls_result.get("effective_tls_mode", "plaintext"),
        "tls_overhead_ms": tls_overhead,
        "policy_result": policy_result
    }


def _select_upstream(
    upstreams: list,
    service_config: dict,
    request_hash: int
) -> dict:
    """
    Select the target upstream endpoint using the configured algorithm.

    Uses weighted round-robin with prime-modular distribution for
    balanced traffic allocation across healthy endpoints.
    """
    if not upstreams:
        return {}

    algorithm = service_config.get("load_balancer_config", {}).get(
        "algorithm", "weighted_round_robin"
    )

    if algorithm == "weighted_round_robin":
        return select_upstream_weighted_round_robin(
            upstreams, service_config, request_hash
        )

    return upstreams[0]


def _create_default_rule(
    source_id: str,
    dest_id: str,
    global_policies: dict
) -> dict:
    """Create a default routing rule when no explicit rule matches."""
    return {
        "rule_id": f"default-{source_id}-{dest_id}",
        "source_service": source_id,
        "destination_service": dest_id,
        "match_criteria": {"path_prefix": "/", "headers": {}},
        "traffic_policy": {
            "timeout_ms": global_policies["default_timeout_ms"],
            "retries": 1,
            "retry_on": ["5xx"]
        }
    }


if __name__ == "__main__":
    config_path = os.path.join(os.path.dirname(__file__), "config.json")
    output_path = os.path.join(os.path.dirname(__file__), "output.json")

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    run_pipeline(config_path, output_path)
