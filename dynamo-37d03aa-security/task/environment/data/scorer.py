"""Compliance scorer for CIS benchmark evaluation.

Computes compliance scores at multiple levels: overall, per-section,
and per-control. Supports both equal-weight and CVSS risk-weighted
scoring methodologies.

Scoring conventions:
- Only "scored" controls contribute to pass percentage
- "informational" controls are reported but excluded from scoring
- Waived controls are counted as passing (accepted risk)
- CVSS weighting uses normalized scores for risk-proportional assessment
"""

from typing import Any


def compute_scores(results: list[dict[str, Any]],
                   risk_weighted: bool = True,
                   scope: str = "control") -> dict[str, Any]:
    """Compute compliance scores from evaluation results.

    Args:
        results: List of evaluation results with status fields
        risk_weighted: If True, weight scores by CVSS. If False, equal weight.
        scope: Aggregation scope - "control" for per-control tallying,
               "section" for section-level aggregation

    Returns:
        Dictionary with overall score, per-section scores, and detailed breakdown.
    """
    # Filter to scored controls only (informational excluded from pass percentage)
    scored_results = [r for r in results if r.get("control_type") == "scored"]
    informational_results = [r for r in results if r.get("control_type") == "informational"]

    if scope == "control":
        overall_score = _compute_control_level_score(scored_results, risk_weighted)
        section_scores = _compute_per_section_scores(scored_results, risk_weighted)
    else:
        overall_score = _compute_section_level_score(scored_results, risk_weighted)
        section_scores = _compute_section_aggregated_scores(scored_results, risk_weighted)

    return {
        "overall_compliance_score": overall_score,
        "section_scores": section_scores,
        "total_controls_evaluated": len(results),
        "scored_controls": len(scored_results),
        "informational_controls": len(informational_results),
        "controls_passed": _count_by_status(scored_results, "pass"),
        "controls_failed": _count_by_status(scored_results, "fail"),
        "controls_waived": _count_by_status(scored_results, "waived"),
    }


def _compute_control_level_score(results: list[dict[str, Any]],
                                  risk_weighted: bool) -> float:
    """Compute overall compliance score at control-level granularity.

    Each control contributes individually to the score.
    With risk weighting, higher-CVSS controls have more impact.
    """
    if not results:
        return 1.0

    if risk_weighted:
        return _weighted_score(results)
    else:
        passed = sum(1 for r in results if r["status"] in ("pass", "waived"))
        return passed / len(results)


def _compute_section_level_score(results: list[dict[str, Any]],
                                  risk_weighted: bool) -> float:
    """Compute overall score using section-level aggregation.

    First determines section pass/fail (a section passes if ALL its
    controls pass), then computes the percentage of passing sections.
    This is a stricter scoring mode used for executive reporting.
    """
    sections = _group_by_section(results)
    if not sections:
        return 1.0

    section_statuses = []
    for section_id, section_results in sections.items():
        all_pass = all(
            r["status"] in ("pass", "waived") for r in section_results
        )
        section_statuses.append({
            "section_id": section_id,
            "passed": all_pass,
            "cvss_max": max(r.get("cvss_score", 5.0) for r in section_results),
        })

    if risk_weighted:
        total_weight = sum(s["cvss_max"] for s in section_statuses)
        if total_weight == 0:
            return 1.0
        weighted_pass = sum(
            s["cvss_max"] for s in section_statuses if s["passed"]
        )
        return weighted_pass / total_weight
    else:
        passed_sections = sum(1 for s in section_statuses if s["passed"])
        return passed_sections / len(section_statuses)


def _compute_per_section_scores(results: list[dict[str, Any]],
                                 risk_weighted: bool) -> dict[str, dict[str, Any]]:
    """Compute individual scores for each section at control granularity."""
    sections = _group_by_section(results)
    scores = {}

    for section_id, section_results in sections.items():
        if risk_weighted:
            score = _weighted_score(section_results)
        else:
            passed = sum(1 for r in section_results if r["status"] in ("pass", "waived"))
            score = passed / len(section_results) if section_results else 1.0

        scores[section_id] = {
            "score": score,
            "total_controls": len(section_results),
            "passed": _count_by_status(section_results, "pass"),
            "failed": _count_by_status(section_results, "fail"),
            "waived": _count_by_status(section_results, "waived"),
        }

    return scores


def _compute_section_aggregated_scores(results: list[dict[str, Any]],
                                        risk_weighted: bool) -> dict[str, dict[str, Any]]:
    """Compute section scores using section-level pass/fail logic.

    A section score is binary: 1.0 if all controls pass, 0.0 if any fails.
    """
    sections = _group_by_section(results)
    scores = {}

    for section_id, section_results in sections.items():
        all_pass = all(
            r["status"] in ("pass", "waived") for r in section_results
        )
        scores[section_id] = {
            "score": 1.0 if all_pass else 0.0,
            "total_controls": len(section_results),
            "passed": _count_by_status(section_results, "pass"),
            "failed": _count_by_status(section_results, "fail"),
            "waived": _count_by_status(section_results, "waived"),
        }

    return scores


def _weighted_score(results: list[dict[str, Any]]) -> float:
    """Compute CVSS-weighted compliance score.

    Weight each control by its CVSS score. Higher severity controls
    contribute more to the overall score. This provides risk-proportional
    compliance measurement.
    """
    if not results:
        return 1.0

    total_weight = 0.0
    passing_weight = 0.0

    for result in results:
        cvss = result.get("cvss_score", 5.0)
        total_weight += cvss
        if result["status"] in ("pass", "waived"):
            passing_weight += cvss

    if total_weight == 0:
        return 1.0

    return passing_weight / total_weight


def _group_by_section(results: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Group results by their parent section.

    Uses the full_path to determine section membership.
    Format: profile/section/subsection/control_id
    The section is determined by the second-to-last path component.
    """
    sections: dict[str, list[dict[str, Any]]] = {}
    for result in results:
        full_path = result.get("full_path", result.get("control_id", ""))
        parts = full_path.split("/")
        # Section is the parent of the control (second-to-last component)
        if len(parts) >= 2:
            section_id = parts[-2]
        else:
            section_id = "default"
        if section_id not in sections:
            sections[section_id] = []
        sections[section_id].append(result)
    return sections


def _count_by_status(results: list[dict[str, Any]], status: str) -> int:
    """Count results with the given status."""
    return sum(1 for r in results if r.get("status") == status)
