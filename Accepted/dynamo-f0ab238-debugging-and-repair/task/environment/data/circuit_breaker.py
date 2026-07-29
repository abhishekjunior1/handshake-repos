"""Circuit breaker state evaluation for service mesh endpoints."""

from typing import Any


# Circuit breaker states
STATE_CLOSED = "closed"
STATE_OPEN = "open"
STATE_HALF_OPEN = "half_open"


def evaluate_circuit_breaker(
    service_id: str,
    upstream_id: str,
    service_config: dict,
    traffic_history: list
) -> dict:
    """
    Evaluate circuit breaker state for a service-to-upstream connection.

    The circuit breaker monitors error rates between a service and its
    upstream endpoint. When the error threshold is exceeded, the circuit
    opens to prevent cascading failures.

    Args:
        service_id: The service whose circuit breaker is being evaluated
        upstream_id: The specific upstream endpoint being monitored
        service_config: The service configuration including CB settings
        traffic_history: List of recent traffic samples for error rate computation

    Returns:
        Circuit breaker evaluation result with state and metrics
    """
    cb_config = service_config.get("circuit_breaker", {})

    if not cb_config.get("enabled", False):
        return {
            "service_id": service_id,
            "upstream_id": upstream_id,
            "state": STATE_CLOSED,
            "enabled": False,
            "error_rate_percent": 0.0,
            "threshold_percent": 0,
            "requests_in_window": 0,
            "action": "allow"
        }

    error_threshold = cb_config.get("error_threshold_percent", 50)
    recovery_timeout_ms = cb_config.get("recovery_timeout_ms", 30000)
    half_open_requests = cb_config.get("half_open_requests", 3)

    relevant_traffic = _filter_traffic_for_pair(
        traffic_history, service_id, upstream_id
    )

    error_rate = _compute_error_rate(relevant_traffic)
    state = _determine_state(error_rate, error_threshold, relevant_traffic,
                             recovery_timeout_ms)
    action = _determine_action(state, half_open_requests, relevant_traffic)

    return {
        "service_id": service_id,
        "upstream_id": upstream_id,
        "state": state,
        "enabled": True,
        "error_rate_percent": round(error_rate, 2),
        "threshold_percent": error_threshold,
        "requests_in_window": len(relevant_traffic),
        "action": action
    }


def _filter_traffic_for_pair(
    traffic_history: list,
    service_id: str,
    upstream_id: str
) -> list:
    """Filter traffic history for a specific service-upstream pair."""
    return [
        t for t in traffic_history
        if t.get("source") == service_id or t.get("destination") == upstream_id
    ]


def _compute_error_rate(traffic: list) -> float:
    """Compute error rate as percentage of failed requests."""
    if not traffic:
        return 0.0

    errors = sum(1 for t in traffic if t.get("status_code", 200) >= 500)
    return (errors / len(traffic)) * 100.0


def _determine_state(
    error_rate: float,
    threshold: int,
    traffic: list,
    recovery_timeout_ms: int
) -> str:
    """
    Determine circuit breaker state based on error rate and history.

    State transitions:
    - CLOSED -> OPEN: error_rate >= threshold (with minimum request count)
    - OPEN -> HALF_OPEN: recovery timeout elapsed
    - HALF_OPEN -> CLOSED: consecutive successes meet half_open_requests count
    - HALF_OPEN -> OPEN: any failure during probe phase
    """
    min_requests = 5

    if len(traffic) < min_requests:
        return STATE_CLOSED

    if error_rate >= threshold:
        return STATE_OPEN

    return STATE_CLOSED


def _determine_action(
    state: str,
    half_open_requests: int,
    traffic: list
) -> str:
    """Determine the routing action based on circuit breaker state."""
    if state == STATE_CLOSED:
        return "allow"
    elif state == STATE_OPEN:
        return "reject"
    elif state == STATE_HALF_OPEN:
        return "probe"
    return "allow"


def compute_health_impact(cb_result: dict) -> float:
    """
    Compute the health impact factor from circuit breaker state.

    This factor is used to adjust the effective weight of an upstream
    based on its circuit breaker state:
    - CLOSED: 1.0 (full capacity)
    - HALF_OPEN: 0.3 (limited probe traffic)
    - OPEN: 0.0 (no traffic)
    """
    state = cb_result.get("state", STATE_CLOSED)

    if state == STATE_CLOSED:
        return 1.0
    elif state == STATE_HALF_OPEN:
        return 0.3
    elif state == STATE_OPEN:
        return 0.0

    return 1.0


def format_cb_summary(cb_results: list) -> dict:
    """
    Format circuit breaker results into a summary report.

    Aggregates per-upstream CB states into service-level health metrics.
    """
    if not cb_results:
        return {"total_evaluated": 0, "open_circuits": 0, "health_factor": 1.0}

    open_count = sum(1 for r in cb_results if r["state"] == STATE_OPEN)
    half_open_count = sum(1 for r in cb_results if r["state"] == STATE_HALF_OPEN)
    total = len(cb_results)

    health_factor = 1.0 - (open_count / total) - (half_open_count * 0.3 / total)
    health_factor = max(0.0, min(1.0, health_factor))

    return {
        "total_evaluated": total,
        "open_circuits": open_count,
        "half_open_circuits": half_open_count,
        "health_factor": round(health_factor, 4)
    }
