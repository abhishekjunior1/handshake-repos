"""Report generator for CIS compliance evaluation results.

Formats evaluation results into a structured compliance report with
executive summary, detailed findings, and section-level breakdowns.
Outputs JSON conforming to the compliance report schema.
"""

import json
from typing import Any


def generate_report(scores: dict[str, Any],
                    evaluation_results: list[dict[str, Any]],
                    waiver_stats: dict[str, Any],
                    config_metadata: dict[str, Any]) -> dict[str, Any]:
    """Generate the final compliance report.

    Produces a structured report with:
    - summary: high-level compliance metrics
    - section_breakdown: per-section scores and findings
    - control_details: individual control results
    - waiver_summary: waiver application statistics
    - metadata: evaluation context
    """
    report = {
        "summary": _build_summary(scores, config_metadata),
        "section_breakdown": _build_section_breakdown(scores),
        "control_details": _build_control_details(evaluation_results),
        "waiver_summary": _build_waiver_summary(waiver_stats),
        "metadata": _build_metadata(config_metadata, scores),
    }

    return report


def _build_summary(scores: dict[str, Any],
                   config_metadata: dict[str, Any]) -> dict[str, Any]:
    """Build executive summary section."""
    overall_score = scores.get("overall_compliance_score", 0.0)
    fail_threshold = config_metadata.get("fail_threshold", 0.7)

    compliance_status = "PASS" if overall_score >= fail_threshold else "FAIL"

    return {
        "overall_compliance_score": round(overall_score, 6),
        "compliance_status": compliance_status,
        "total_controls_evaluated": scores.get("total_controls_evaluated", 0),
        "scored_controls": scores.get("scored_controls", 0),
        "informational_controls": scores.get("informational_controls", 0),
        "controls_passed": scores.get("controls_passed", 0),
        "controls_failed": scores.get("controls_failed", 0),
        "controls_waived": scores.get("controls_waived", 0),
        "pass_rate": _compute_pass_rate(scores),
    }


def _compute_pass_rate(scores: dict[str, Any]) -> float:
    """Compute the simple pass rate (passed / total scored)."""
    scored = scores.get("scored_controls", 0)
    if scored == 0:
        return 1.0
    passed = scores.get("controls_passed", 0) + scores.get("controls_waived", 0)
    return round(passed / scored, 6)


def _build_section_breakdown(scores: dict[str, Any]) -> list[dict[str, Any]]:
    """Build per-section breakdown with scores and control counts."""
    section_scores = scores.get("section_scores", {})
    breakdown = []

    for section_id, section_data in sorted(section_scores.items()):
        breakdown.append({
            "section_id": section_id,
            "compliance_score": round(section_data.get("score", 0.0), 6),
            "total_controls": section_data.get("total_controls", 0),
            "passed": section_data.get("passed", 0),
            "failed": section_data.get("failed", 0),
            "waived": section_data.get("waived", 0),
        })

    return breakdown


def _build_control_details(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build detailed per-control results."""
    details = []
    for result in sorted(results, key=lambda r: r.get("control_id", "")):
        detail = {
            "control_id": result.get("control_id", ""),
            "resource_id": result.get("resource_id", ""),
            "status": result.get("status", "not_evaluated"),
            "severity": result.get("severity", "medium"),
            "cvss_score": result.get("cvss_score", 5.0),
            "control_type": result.get("control_type", "scored"),
            "full_path": result.get("full_path", ""),
            "evidence": result.get("evidence", []),
        }

        # Include waiver information if applicable
        if result.get("status") == "waived":
            detail["waiver_id"] = result.get("waiver_id", "")
            detail["waiver_reason"] = result.get("waiver_reason", "")
            detail["original_status"] = result.get("original_status", "fail")

        details.append(detail)

    return details


def _build_waiver_summary(waiver_stats: dict[str, Any]) -> dict[str, Any]:
    """Build waiver application summary."""
    return {
        "total_waivers_applied": waiver_stats.get("total_waived", 0),
        "waivers_by_severity": waiver_stats.get("by_severity", {}),
        "waivers_by_type": waiver_stats.get("by_type", {}),
        "unique_waivers_used": waiver_stats.get("unique_waivers_applied", 0),
    }


def _build_metadata(config_metadata: dict[str, Any],
                    scores: dict[str, Any]) -> dict[str, Any]:
    """Build evaluation metadata."""
    return {
        "evaluation_profile": config_metadata.get("evaluation_profile", ""),
        "scoring_method": "cvss_risk_weighted" if config_metadata.get(
            "risk_weighted_scoring", True) else "equal_weight",
        "fail_threshold": config_metadata.get("fail_threshold", 0.7),
        "inheritance_mode": config_metadata.get("inheritance_mode", "full_chain"),
        "exception_match_mode": config_metadata.get("exception_match_mode", "glob"),
    }


def write_report(report: dict[str, Any], output_path: str) -> None:
    """Write the compliance report to a JSON file."""
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
