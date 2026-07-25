"""
Report formatter for compliance assessment output.
Formats assessment results into structured JSON report.
"""

import json


def format_compliance_report(
    assessment_results: list,
    scores: dict,
    exemption_map: dict,
    scope_coverage: dict,
    severity_distribution: dict,
    critical_findings: list,
    risk_score: float,
    config_metadata: dict,
) -> dict:
    """
    Format full compliance report combining all assessment data.
    Returns structured dict ready for JSON serialization.
    """
    report = {
        "metadata": _format_metadata(config_metadata),
        "summary": _format_summary(scores, risk_score, scope_coverage),
        "compliance_scores": scores,
        "severity_distribution": severity_distribution,
        "critical_findings": critical_findings,
        "risk_score": risk_score,
        "waivers_applied": _format_waivers(exemption_map),
        "scope_coverage": scope_coverage,
        "detailed_results": _format_detailed_results(assessment_results),
    }

    return report


def _format_metadata(config_metadata: dict) -> dict:
    """Format report metadata section."""
    return {
        "report_version": "1.0",
        "framework": config_metadata.get("framework", "CIS"),
        "benchmark_version": config_metadata.get("benchmark_version", "1.0"),
        "assessment_scope": config_metadata.get("assessment_scope", "full"),
        "evaluation_date": config_metadata.get("evaluation_date", ""),
    }


def _format_summary(scores: dict, risk_score: float, scope_coverage: dict) -> dict:
    """Format executive summary section."""
    overall = scores.get("overall_score", 0.0)

    if overall >= 0.9:
        posture = "strong"
    elif overall >= 0.7:
        posture = "moderate"
    elif overall >= 0.5:
        posture = "weak"
    else:
        posture = "critical"

    return {
        "overall_compliance": overall,
        "security_posture": posture,
        "risk_score": risk_score,
        "resources_assessed": scope_coverage.get("resources_in_scope", 0),
        "rules_evaluated": scope_coverage.get("rules_in_scope", 0),
    }


def _format_waivers(exemption_map: dict) -> list:
    """Format applied waivers for report."""
    waivers_list = []
    for (resource_id, rule_id), waiver_info in sorted(exemption_map.items()):
        waivers_list.append({
            "resource_id": resource_id,
            "rule_id": rule_id,
            "waiver_id": waiver_info["waiver_id"],
            "reason": waiver_info["reason"],
        })
    return waivers_list


def _format_detailed_results(assessment_results: list) -> list:
    """Format individual assessment results for detailed view."""
    formatted = []
    for result in sorted(assessment_results, key=lambda r: (r["resource_id"], r["rule_id"])):
        formatted.append({
            "resource_id": result["resource_id"],
            "rule_id": result["rule_id"],
            "status": result["status"],
            "details": result.get("details", ""),
        })
    return formatted


def write_report(report: dict, output_path: str) -> None:
    """Write formatted report to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)


def compute_report_statistics(report: dict) -> dict:
    """Compute summary statistics from a formatted report."""
    results = report.get("detailed_results", [])
    total = len(results)
    passing = sum(1 for r in results if r["status"] == "pass")
    failing = sum(1 for r in results if r["status"] == "fail")
    waived = sum(1 for r in results if r["status"] == "waived")

    return {
        "total_assessments": total,
        "passing": passing,
        "failing": failing,
        "waived": waived,
        "pass_rate": round(passing / total * 100, 2) if total > 0 else 0.0,
    }
