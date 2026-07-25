"""Service mesh configuration loader and validator."""

import json
import sys
from typing import Any


REQUIRED_SERVICE_FIELDS = [
    "service_id", "namespace", "port", "protocol",
    "mtls_required", "health_check_path", "load_balancer_config",
    "circuit_breaker", "upstreams"
]

REQUIRED_UPSTREAM_FIELDS = [
    "upstream_id", "address", "port", "weight",
    "priority", "health_score", "zone"
]

SUPPORTED_PROTOCOLS = ["HTTP", "gRPC", "TCP", "HTTP2"]
SUPPORTED_LB_ALGORITHMS = ["weighted_round_robin", "least_connections", "random", "ring_hash"]


def load_config(config_path: str) -> dict:
    """Load and validate the service mesh configuration file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)

    _validate_global_policies(config)
    _validate_services(config)
    _validate_routing_rules(config)
    _validate_traffic_samples(config)

    return config


def _validate_global_policies(config: dict) -> None:
    """Validate global policy settings."""
    if "global_policies" not in config:
        raise ValueError("Missing global_policies section")

    policies = config["global_policies"]
    required = ["mtls_mode", "default_timeout_ms", "retry_budget_percent",
                "circuit_breaker_threshold"]

    for field in required:
        if field not in policies:
            raise ValueError(f"Missing global policy: {field}")

    if policies["mtls_mode"] not in ["disabled", "permissive", "strict"]:
        raise ValueError(f"Invalid mtls_mode: {policies['mtls_mode']}")

    if not (0 < policies["default_timeout_ms"] <= 300000):
        raise ValueError("default_timeout_ms must be between 1 and 300000")

    if not (0 <= policies["retry_budget_percent"] <= 100):
        raise ValueError("retry_budget_percent must be between 0 and 100")


def _validate_services(config: dict) -> None:
    """Validate service definitions and their upstreams."""
    if "services" not in config or not config["services"]:
        raise ValueError("At least one service must be defined")

    service_ids = set()
    for service in config["services"]:
        for field in REQUIRED_SERVICE_FIELDS:
            if field not in service:
                raise ValueError(f"Service missing field: {field}")

        if service["service_id"] in service_ids:
            raise ValueError(f"Duplicate service_id: {service['service_id']}")
        service_ids.add(service["service_id"])

        if service["protocol"] not in SUPPORTED_PROTOCOLS:
            raise ValueError(f"Unsupported protocol: {service['protocol']}")

        lb_config = service["load_balancer_config"]
        if lb_config.get("algorithm") not in SUPPORTED_LB_ALGORITHMS:
            raise ValueError(f"Unsupported LB algorithm: {lb_config.get('algorithm')}")

        _validate_upstreams(service)


def _validate_upstreams(service: dict) -> None:
    """Validate upstream endpoints for a service."""
    if not service["upstreams"]:
        raise ValueError(f"Service {service['service_id']} has no upstreams")

    for upstream in service["upstreams"]:
        for field in REQUIRED_UPSTREAM_FIELDS:
            if field not in upstream:
                raise ValueError(
                    f"Upstream in {service['service_id']} missing: {field}"
                )

        if not (0 <= upstream["weight"] <= 1000):
            raise ValueError(f"Invalid weight: {upstream['weight']}")

        if not (0.0 <= upstream["health_score"] <= 1.0):
            raise ValueError(f"Invalid health_score: {upstream['health_score']}")


def _validate_routing_rules(config: dict) -> None:
    """Validate routing rule definitions."""
    if "routing_rules" not in config:
        raise ValueError("Missing routing_rules section")

    service_ids = {s["service_id"] for s in config["services"]}
    rule_ids = set()

    for rule in config["routing_rules"]:
        if rule["rule_id"] in rule_ids:
            raise ValueError(f"Duplicate rule_id: {rule['rule_id']}")
        rule_ids.add(rule["rule_id"])

        if rule["source_service"] not in service_ids:
            raise ValueError(f"Unknown source: {rule['source_service']}")

        if rule["destination_service"] not in service_ids:
            raise ValueError(f"Unknown destination: {rule['destination_service']}")


def _validate_traffic_samples(config: dict) -> None:
    """Validate traffic sample entries."""
    if "traffic_samples" not in config:
        raise ValueError("Missing traffic_samples section")

    service_ids = {s["service_id"] for s in config["services"]}

    for sample in config["traffic_samples"]:
        required = ["request_id", "source", "destination", "path",
                    "headers", "timestamp_ms"]
        for field in required:
            if field not in sample:
                raise ValueError(f"Traffic sample missing: {field}")

        if sample["source"] not in service_ids:
            raise ValueError(f"Unknown traffic source: {sample['source']}")

        if sample["destination"] not in service_ids:
            raise ValueError(f"Unknown traffic destination: {sample['destination']}")


def get_service_map(config: dict) -> dict:
    """Build a lookup map from service_id to service config."""
    return {s["service_id"]: s for s in config["services"]}


def get_routing_table(config: dict) -> list:
    """Return sorted routing rules by specificity (most specific first)."""
    rules = config["routing_rules"][:]
    rules.sort(key=lambda r: (-len(r["match_criteria"].get("headers", {})),
                              -len(r["match_criteria"].get("path_prefix", ""))))
    return rules
