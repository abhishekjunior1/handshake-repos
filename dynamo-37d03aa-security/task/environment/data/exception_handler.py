"""Exception and waiver handler for CIS compliance evaluation.

Processes waiver/exception definitions that exempt specific resources
from certain controls. Supports both exact match and glob pattern
matching for resource identification.

Waivers represent approved deviations from compliance requirements:
- Temporary waivers: time-bounded exceptions with expiration
- Permanent waivers: accepted risk for specific resource/control pairs
- Pattern waivers: glob-based matching for resource groups
"""

import fnmatch
from typing import Any
from datetime import datetime


def apply_waivers(evaluation_results: list[dict[str, Any]],
                  waivers: list[dict[str, Any]],
                  match_mode: str = "glob") -> list[dict[str, Any]]:
    """Apply waivers to evaluation results, marking waived failures.

    Args:
        evaluation_results: List of control evaluation results
        waivers: List of waiver definitions
        match_mode: "glob" for pattern matching, "exact" for literal match

    Returns:
        Updated evaluation results with waiver annotations.
    """
    if not waivers:
        return evaluation_results

    active_waivers = _filter_active_waivers(waivers)
    if not active_waivers:
        return evaluation_results

    updated_results = []
    for result in evaluation_results:
        waiver_match = _find_matching_waiver(
            result, active_waivers, match_mode
        )
        if waiver_match and result["status"] == "fail":
            result = dict(result)
            result["status"] = "waived"
            result["waiver_id"] = waiver_match["id"]
            result["waiver_reason"] = waiver_match.get("reason", "")
            result["original_status"] = "fail"
        updated_results.append(result)

    return updated_results


def _filter_active_waivers(waivers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Filter waivers to only include currently active ones.

    A waiver is active if:
    - It has no expiration date, OR
    - Its expiration date is in the future
    """
    active = []
    now = datetime.utcnow()

    for waiver in waivers:
        if "expires" in waiver:
            try:
                expiry = datetime.fromisoformat(waiver["expires"])
                if expiry < now:
                    continue
            except (ValueError, TypeError):
                continue
        active.append(waiver)

    return active


def _find_matching_waiver(result: dict[str, Any],
                          waivers: list[dict[str, Any]],
                          match_mode: str) -> dict[str, Any] | None:
    """Find the first waiver that matches the given evaluation result.

    Matching is performed on both resource_id and control_id.
    The match_mode determines how resource patterns are interpreted:
    - "glob": uses fnmatch for glob-style pattern matching
    - "exact": requires exact string equality
    """
    resource_id = result.get("resource_id", "")
    control_id = result.get("control_id", "")

    for waiver in waivers:
        if _waiver_matches(waiver, resource_id, control_id, match_mode):
            return waiver

    return None


def _waiver_matches(waiver: dict[str, Any], resource_id: str,
                    control_id: str, match_mode: str) -> bool:
    """Check if a waiver matches the resource and control combination.

    A waiver matches if:
    1. The resource_pattern matches the resource_id (per match_mode)
    2. The control_pattern matches the control_id (per match_mode)
    """
    resource_pattern = waiver.get("resource_pattern", "*")
    control_pattern = waiver.get("control_pattern", "*")

    resource_matches = _pattern_matches(
        resource_pattern, resource_id, match_mode
    )
    control_matches = _pattern_matches(
        control_pattern, control_id, match_mode
    )

    return resource_matches and control_matches


def _pattern_matches(pattern: str, value: str, mode: str) -> bool:
    """Match a pattern against a value using the specified mode.

    Glob mode: supports *, ?, [seq], [!seq] patterns
    Exact mode: requires exact string equality
    """
    if mode == "glob":
        return fnmatch.fnmatch(value, pattern)
    elif mode == "exact":
        return pattern == value
    else:
        return pattern == value


def compute_waiver_statistics(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute statistics about waiver application.

    Returns counts of waived controls by severity and type.
    """
    waived = [r for r in results if r.get("status") == "waived"]

    severity_counts: dict[str, int] = {}
    type_counts: dict[str, int] = {}
    waiver_ids: set[str] = set()

    for result in waived:
        severity = result.get("severity", "unknown")
        severity_counts[severity] = severity_counts.get(severity, 0) + 1

        control_type = result.get("control_type", "unknown")
        type_counts[control_type] = type_counts.get(control_type, 0) + 1

        waiver_id = result.get("waiver_id", "")
        if waiver_id:
            waiver_ids.add(waiver_id)

    return {
        "total_waived": len(waived),
        "by_severity": severity_counts,
        "by_type": type_counts,
        "unique_waivers_applied": len(waiver_ids),
        "waiver_ids": sorted(waiver_ids),
    }


def validate_waiver_coverage(waivers: list[dict[str, Any]],
                             results: list[dict[str, Any]],
                             match_mode: str = "glob") -> dict[str, Any]:
    """Validate which waivers were actually applied vs unused.

    Identifies:
    - Applied waivers: matched at least one failed control
    - Unused waivers: defined but matched no failures
    - Overscoped waivers: patterns that match too many resources
    """
    applied_ids: set[str] = set()
    all_ids: set[str] = set()

    for waiver in waivers:
        all_ids.add(waiver.get("id", ""))

    for result in results:
        if result.get("status") == "waived":
            applied_ids.add(result.get("waiver_id", ""))

    unused_ids = all_ids - applied_ids

    return {
        "applied_waivers": sorted(applied_ids),
        "unused_waivers": sorted(unused_ids),
        "coverage_ratio": len(applied_ids) / max(len(all_ids), 1),
    }
