"""Traffic policy enforcement and decision aggregation for service mesh."""

from typing import Any


# Policy decision outcomes
DECISION_ALLOW = "allow"
DECISION_DENY = "deny"
DECISION_RATE_LIMIT = "rate_limit"

# Enforcement modes
MODE_ENFORCE = "enforce"
MODE_AUDIT = "audit"
MODE_SHADOW = "shadow"


def enforce_traffic_policy(
    mtls_result: dict,
    routing_result: dict,
    cb_result: dict,
    health_result: dict,
    service_config: dict
) -> dict:
    """
    Make final traffic policy decision based on all evaluation components.

    Policy enforcement follows a strict decision hierarchy:
    1. mTLS validation failure → DENY (security takes absolute precedence)
    2. Circuit breaker OPEN → DENY (prevent cascading failures)
    3. Health check CRITICAL → DENY (endpoint unavailable)
    4. All checks pass → ALLOW with computed metrics

    This hierarchy ensures security violations are caught before any
    routing or load balancing decisions are made.
    """
    decision = DECISION_ALLOW
    deny_reasons = []
    warnings = []

    if mtls_result.get("validation_status") == "fail":
        decision = DECISION_DENY
        deny_reasons.extend(mtls_result.get("policy_violations", []))

    if cb_result.get("action") == "reject":
        decision = DECISION_DENY
        deny_reasons.append(
            f"circuit breaker open for {cb_result.get('upstream_id', 'unknown')}"
        )

    if health_result.get("status") == "critical":
        decision = DECISION_DENY
        deny_reasons.append(
            f"endpoint {health_result.get('upstream_id', '')} health critical"
        )

    if mtls_result.get("policy_violations") and decision == DECISION_ALLOW:
        warnings.extend(mtls_result["policy_violations"])

    if health_result.get("status") == "warning":
        warnings.append(
            f"endpoint {health_result.get('upstream_id', '')} health degraded"
        )

    return {
        "decision": decision,
        "deny_reasons": deny_reasons,
        "warnings": warnings,
        "mtls_status": mtls_result.get("validation_status", "skip"),
        "cb_state": cb_result.get("state", "closed"),
        "health_status": health_result.get("status", "passing"),
        "effective_timeout_ms": routing_result.get("effective_timeout_ms", 0),
        "selected_upstream": routing_result.get("selected_upstream", ""),
        "tls_mode": mtls_result.get("effective_tls_mode", "plaintext")
    }


def compute_policy_score(enforcement_result: dict) -> float:
    """
    Compute a numeric policy compliance score (0.0 to 1.0).

    Scoring breakdown:
    - Base: 1.0 for ALLOW, 0.0 for DENY
    - Penalty: -0.1 per warning
    - Bonus: +0.05 for mutual_tls mode
    """
    if enforcement_result["decision"] == DECISION_DENY:
        return 0.0

    score = 1.0
    score -= len(enforcement_result.get("warnings", [])) * 0.1
    score = max(0.0, score)

    if enforcement_result.get("tls_mode") == "mutual_tls":
        score = min(1.0, score + 0.05)

    return round(score, 4)


def aggregate_policy_results(policy_results: list) -> dict:
    """
    Aggregate multiple policy evaluation results into a mesh-wide summary.

    Computes allow/deny rates, warning counts, and overall mesh health score.
    """
    if not policy_results:
        return {
            "total_evaluations": 0,
            "allowed": 0,
            "denied": 0,
            "allow_rate_percent": 0.0,
            "total_warnings": 0,
            "average_policy_score": 0.0,
            "mesh_health_score": 0.0
        }

    allowed = sum(1 for r in policy_results if r["decision"] == DECISION_ALLOW)
    denied = sum(1 for r in policy_results if r["decision"] == DECISION_DENY)
    total = len(policy_results)

    all_warnings = sum(len(r.get("warnings", [])) for r in policy_results)
    scores = [compute_policy_score(r) for r in policy_results]
    avg_score = sum(scores) / len(scores) if scores else 0.0

    mesh_health = (allowed / total) * avg_score if total > 0 else 0.0

    return {
        "total_evaluations": total,
        "allowed": allowed,
        "denied": denied,
        "allow_rate_percent": round((allowed / total) * 100, 2) if total > 0 else 0.0,
        "total_warnings": all_warnings,
        "average_policy_score": round(avg_score, 4),
        "mesh_health_score": round(mesh_health, 4)
    }


def format_denial_report(policy_results: list) -> list:
    """Generate a report of all denied traffic with reasons."""
    denials = []
    for r in policy_results:
        if r["decision"] == DECISION_DENY:
            denials.append({
                "selected_upstream": r.get("selected_upstream", ""),
                "deny_reasons": r.get("deny_reasons", []),
                "cb_state": r.get("cb_state", ""),
                "health_status": r.get("health_status", ""),
                "mtls_status": r.get("mtls_status", "")
            })
    return denials
