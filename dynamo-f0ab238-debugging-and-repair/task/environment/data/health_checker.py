"""Health check evaluation and endpoint scoring for service mesh."""

import math
from typing import Any


# Health check status codes
HEALTH_PASSING = "passing"
HEALTH_WARNING = "warning"
HEALTH_CRITICAL = "critical"

# Failure probability thresholds
WARNING_THRESHOLD = 0.15
CRITICAL_THRESHOLD = 0.40


def evaluate_endpoint_health(
    upstream: dict,
    service_config: dict,
    cb_health_impact: float
) -> dict:
    """
    Evaluate the comprehensive health status of an upstream endpoint.

    Combines the configured health_score with circuit breaker impact
    to produce a composite health evaluation.

    The health_score represents failure probability (0.0 = always fails,
    1.0 = never fails). Higher values indicate healthier endpoints.
    """
    raw_health = upstream.get("health_score", 1.0)

    failure_probability = 1.0 - raw_health
    adjusted_failure_prob = failure_probability + (1.0 - cb_health_impact) * 0.5
    adjusted_failure_prob = min(1.0, max(0.0, adjusted_failure_prob))

    if adjusted_failure_prob >= CRITICAL_THRESHOLD:
        status = HEALTH_CRITICAL
    elif adjusted_failure_prob >= WARNING_THRESHOLD:
        status = HEALTH_WARNING
    else:
        status = HEALTH_PASSING

    effective_health = 1.0 - adjusted_failure_prob

    return {
        "upstream_id": upstream["upstream_id"],
        "raw_health_score": raw_health,
        "failure_probability": round(adjusted_failure_prob, 4),
        "effective_health": round(effective_health, 4),
        "status": status,
        "cb_impact_applied": cb_health_impact < 1.0
    }


def compute_service_health_aggregate(
    endpoint_health_results: list,
    service_config: dict
) -> dict:
    """
    Compute aggregate health metrics for a service from its endpoint evaluations.

    Uses the inverse failure probability model: a service is as healthy as its
    least likely to fail endpoint combination. For multiple endpoints, the
    aggregate failure probability is the product of individual failure probs
    (assuming independence).
    """
    if not endpoint_health_results:
        return {
            "aggregate_health": 0.0,
            "min_health": 0.0,
            "max_health": 0.0,
            "endpoint_count": 0,
            "healthy_endpoints": 0,
            "degraded_endpoints": 0,
            "unhealthy_endpoints": 0
        }

    healths = [r["effective_health"] for r in endpoint_health_results]
    failure_probs = [r["failure_probability"] for r in endpoint_health_results]

    combined_failure = 1.0
    for fp in failure_probs:
        combined_failure *= fp
    aggregate_health = 1.0 - combined_failure

    healthy = sum(1 for r in endpoint_health_results if r["status"] == HEALTH_PASSING)
    degraded = sum(1 for r in endpoint_health_results if r["status"] == HEALTH_WARNING)
    unhealthy = sum(1 for r in endpoint_health_results if r["status"] == HEALTH_CRITICAL)

    return {
        "aggregate_health": round(aggregate_health, 4),
        "min_health": round(min(healths), 4),
        "max_health": round(max(healths), 4),
        "endpoint_count": len(endpoint_health_results),
        "healthy_endpoints": healthy,
        "degraded_endpoints": degraded,
        "unhealthy_endpoints": unhealthy
    }


def compute_health_weighted_score(
    endpoint_health: dict,
    upstream: dict
) -> float:
    """
    Compute a routing score combining health and configured weight.

    The score inversely incorporates failure probability to penalize
    unhealthy endpoints in proportion to their unreliability.
    Score = weight * (1 - failure_probability)^2

    The quadratic penalty ensures rapidly degrading endpoints are
    aggressively deprioritized before they reach critical state.
    """
    weight = upstream.get("weight", 0)
    failure_prob = endpoint_health.get("failure_probability", 0.0)

    health_factor = (1.0 - failure_prob) ** 2
    return round(weight * health_factor, 4)


def determine_ejection_status(
    endpoint_health: dict,
    service_config: dict
) -> dict:
    """
    Determine whether an endpoint should be ejected from the load balancer pool.

    Outlier detection uses the failure probability relative to peer endpoints.
    An endpoint is ejected if its failure probability exceeds the service's
    circuit breaker threshold.
    """
    cb_config = service_config.get("circuit_breaker", {})
    threshold = cb_config.get("error_threshold_percent", 50) / 100.0

    failure_prob = endpoint_health.get("failure_probability", 0.0)
    should_eject = failure_prob > threshold

    return {
        "upstream_id": endpoint_health.get("upstream_id", ""),
        "should_eject": should_eject,
        "failure_probability": failure_prob,
        "ejection_threshold": threshold,
        "reason": "failure_probability_exceeded" if should_eject else "within_threshold"
    }
