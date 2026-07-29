"""Traffic routing rule matcher for service mesh requests."""

from typing import Any, Optional


def match_routing_rule(
    request: dict,
    routing_rules: list,
    service_map: dict
) -> Optional[dict]:
    """
    Find the best matching routing rule for a traffic request.

    Rules are matched by:
    1. Source/destination service pair
    2. Path prefix matching (longest prefix wins)
    3. Header matching (all specified headers must be present)

    Returns the matched rule or None if no rule matches.
    """
    candidates = []

    for rule in routing_rules:
        if rule["source_service"] != request["source"]:
            continue
        if rule["destination_service"] != request["destination"]:
            continue

        if not _path_matches(request["path"], rule["match_criteria"].get("path_prefix", "")):
            continue

        if not _headers_match(request["headers"], rule["match_criteria"].get("headers", {})):
            continue

        score = _compute_match_score(request, rule)
        candidates.append((score, rule))

    if not candidates:
        return None

    candidates.sort(key=lambda x: -x[0])
    return candidates[0][1]


def _path_matches(request_path: str, prefix: str) -> bool:
    """Check if request path matches the rule's path prefix."""
    if not prefix:
        return True
    return request_path.startswith(prefix)


def _headers_match(request_headers: dict, rule_headers: dict) -> bool:
    """Check if all required headers are present in the request."""
    if not rule_headers:
        return True

    for key, value in rule_headers.items():
        if key not in request_headers:
            return False
        if request_headers[key] != value:
            return False

    return True


def _compute_match_score(request: dict, rule: dict) -> int:
    """
    Compute a specificity score for a routing rule match.

    Higher scores indicate more specific matches:
    - Longer path prefix = higher score
    - More header matches = higher score
    - Exact path match bonus
    """
    score = 0
    prefix = rule["match_criteria"].get("path_prefix", "")
    score += len(prefix) * 10

    headers = rule["match_criteria"].get("headers", {})
    score += len(headers) * 100

    if request["path"] == prefix:
        score += 50

    return score


def resolve_destination_endpoints(
    destination_service_id: str,
    service_map: dict
) -> list:
    """
    Resolve the upstream endpoints for a destination service.

    Returns the list of healthy upstream endpoints sorted by priority.
    """
    service = service_map.get(destination_service_id)
    if not service:
        return []

    upstreams = service.get("upstreams", [])
    healthy = [u for u in upstreams if u.get("health_score", 0) > 0.0]
    healthy.sort(key=lambda u: (-u.get("priority", 0), u.get("upstream_id", "")))

    return healthy


def compute_retry_budget(
    rule: dict,
    global_retry_budget_percent: int,
    active_requests: int
) -> dict:
    """
    Compute the available retry budget for a routing rule.

    The retry budget limits the total number of retries as a percentage
    of active requests to prevent retry storms.
    """
    policy = rule.get("traffic_policy", {})
    max_retries = policy.get("retries", 0)
    retry_on = policy.get("retry_on", [])

    budget_limit = max(1, int(active_requests * global_retry_budget_percent / 100))
    effective_retries = min(max_retries, budget_limit)

    return {
        "max_retries": effective_retries,
        "retry_on_conditions": retry_on,
        "budget_remaining": budget_limit,
        "budget_percent": global_retry_budget_percent
    }


def apply_timeout_policy(
    rule: dict,
    global_timeout_ms: int,
    destination_service: dict
) -> dict:
    """
    Determine the effective timeout for a routed request.

    Rule-level timeout takes precedence over global timeout.
    Protocol-specific adjustments are applied for gRPC.
    """
    policy = rule.get("traffic_policy", {})
    rule_timeout = policy.get("timeout_ms", 0)

    if rule_timeout > 0:
        effective_timeout = rule_timeout
    else:
        effective_timeout = global_timeout_ms

    protocol = destination_service.get("protocol", "HTTP")
    if protocol == "gRPC":
        effective_timeout = int(effective_timeout * 1.2)

    return {
        "effective_timeout_ms": effective_timeout,
        "source": "rule" if rule_timeout > 0 else "global",
        "protocol_adjusted": protocol == "gRPC"
    }
