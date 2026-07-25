"""Report generation for service mesh traffic policy evaluation."""

import json
from typing import Any


def generate_evaluation_report(
    mesh_name: str,
    service_evaluations: list,
    routing_decisions: list,
    policy_summary: dict,
    service_health_map: dict
) -> dict:
    """
    Generate the final evaluation report for the service mesh.

    Combines per-request routing decisions, service health assessments,
    and policy enforcement results into a structured output report.
    """
    report = {
        "mesh_name": mesh_name,
        "evaluation_summary": _build_evaluation_summary(
            routing_decisions, policy_summary
        ),
        "service_health": _build_service_health_section(service_health_map),
        "routing_decisions": _format_routing_decisions(routing_decisions),
        "policy_enforcement": _format_policy_section(policy_summary),
        "recommendations": _generate_recommendations(
            routing_decisions, service_health_map, policy_summary
        )
    }

    return report


def _build_evaluation_summary(
    routing_decisions: list,
    policy_summary: dict
) -> dict:
    """Build the top-level evaluation summary."""
    return {
        "total_requests_evaluated": policy_summary.get("total_evaluations", 0),
        "requests_allowed": policy_summary.get("allowed", 0),
        "requests_denied": policy_summary.get("denied", 0),
        "allow_rate_percent": policy_summary.get("allow_rate_percent", 0.0),
        "mesh_health_score": policy_summary.get("mesh_health_score", 0.0),
        "average_policy_score": policy_summary.get("average_policy_score", 0.0)
    }


def _build_service_health_section(service_health_map: dict) -> dict:
    """Build per-service health status section."""
    health_section = {}

    for service_id, health_data in service_health_map.items():
        health_section[service_id] = {
            "aggregate_health": health_data.get("aggregate_health", 0.0),
            "endpoint_count": health_data.get("endpoint_count", 0),
            "healthy_endpoints": health_data.get("healthy_endpoints", 0),
            "degraded_endpoints": health_data.get("degraded_endpoints", 0),
            "unhealthy_endpoints": health_data.get("unhealthy_endpoints", 0)
        }

    return health_section


def _format_routing_decisions(routing_decisions: list) -> list:
    """Format individual routing decisions for the report."""
    formatted = []

    for decision in routing_decisions:
        entry = {
            "request_id": decision.get("request_id", ""),
            "source": decision.get("source", ""),
            "destination": decision.get("destination", ""),
            "selected_upstream": decision.get("selected_upstream", ""),
            "load_balancer_weight": float(decision.get("lb_weight", 0.0)),
            "effective_timeout_ms": decision.get("effective_timeout_ms", 0),
            "policy_decision": decision.get("policy_decision", ""),
            "tls_mode": decision.get("tls_mode", "plaintext"),
            "tls_overhead_ms": decision.get("tls_overhead_ms", 0.0)
        }
        formatted.append(entry)

    return formatted


def _format_policy_section(policy_summary: dict) -> dict:
    """Format policy enforcement summary."""
    return {
        "total_evaluations": policy_summary.get("total_evaluations", 0),
        "allowed": policy_summary.get("allowed", 0),
        "denied": policy_summary.get("denied", 0),
        "total_warnings": policy_summary.get("total_warnings", 0),
        "average_policy_score": policy_summary.get("average_policy_score", 0.0),
        "mesh_health_score": policy_summary.get("mesh_health_score", 0.0)
    }


def _generate_recommendations(
    routing_decisions: list,
    service_health_map: dict,
    policy_summary: dict
) -> list:
    """
    Generate operational recommendations based on evaluation results.

    Recommendations are prioritized by severity and actionability.
    """
    recommendations = []

    for service_id, health in service_health_map.items():
        if health.get("unhealthy_endpoints", 0) > 0:
            recommendations.append({
                "severity": "high",
                "service": service_id,
                "recommendation": f"Service '{service_id}' has unhealthy endpoints - investigate health check failures"
            })
        elif health.get("degraded_endpoints", 0) > 0:
            recommendations.append({
                "severity": "medium",
                "service": service_id,
                "recommendation": f"Service '{service_id}' has degraded endpoints - monitor for further deterioration"
            })

    if policy_summary.get("denied", 0) > 0:
        deny_rate = (policy_summary["denied"] / max(1, policy_summary.get("total_evaluations", 1))) * 100
        if deny_rate > 20:
            recommendations.append({
                "severity": "high",
                "service": "mesh",
                "recommendation": f"High denial rate ({deny_rate:.1f}%) - review mTLS and circuit breaker configurations"
            })

    mesh_score = policy_summary.get("mesh_health_score", 1.0)
    if mesh_score < 0.8:
        recommendations.append({
            "severity": "medium",
            "service": "mesh",
            "recommendation": f"Mesh health score ({mesh_score:.2f}) below threshold - review service dependencies"
        })

    recommendations.sort(key=lambda r: {"high": 0, "medium": 1, "low": 2}.get(r["severity"], 3))

    return recommendations


def write_report(report: dict, output_path: str) -> None:
    """Write the evaluation report to a JSON file."""
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)
