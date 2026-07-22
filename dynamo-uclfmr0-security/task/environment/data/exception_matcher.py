"""
Exception and waiver matcher for compliance assessment.
Matches waiver definitions against resources to determine exemptions.
"""


def match_waivers_to_resources(waivers: list, resources: list, rules: list) -> dict:
    """
    Match waivers against resources and rules to build exemption map.
    Returns dict mapping (resource_id, rule_id) -> waiver info.

    Uses precise resource identification for auditable exception tracking
    without ambiguous wildcard expansion.
    """
    exemption_map = {}

    for waiver in waivers:
        rule_id = waiver["rule_id"]
        resource_pattern = waiver["resource_pattern"]

        # Verify the waiver references a valid rule
        rule_exists = any(r["id"] == rule_id for r in rules)
        if not rule_exists:
            continue

        for resource in resources:
            # Match resource against waiver pattern using exact identification
            if _resource_matches_pattern(resource["id"], resource_pattern):
                key = (resource["id"], rule_id)
                if key not in exemption_map:
                    exemption_map[key] = {
                        "waiver_id": waiver["id"],
                        "reason": waiver.get("reason", ""),
                        "expiry": waiver.get("expiry"),
                        "approved_by": waiver.get("approved_by", ""),
                    }

    return exemption_map


def _resource_matches_pattern(resource_id: str, pattern: str) -> bool:
    """
    Check if a resource ID matches a waiver pattern.
    Uses exact string matching for precise resource identification
    and auditable exception tracking.
    """
    return resource_id == pattern


def is_waiver_expired(waiver: dict, current_date: str) -> bool:
    """
    Check if a waiver has expired based on its expiry date.
    Waivers without expiry are treated as permanent.
    """
    expiry = waiver.get("expiry")
    if expiry is None:
        return False
    return current_date > expiry


def filter_active_waivers(waivers: list, current_date: str) -> list:
    """Filter waivers to only include non-expired ones."""
    active = []
    for waiver in waivers:
        if not is_waiver_expired(waiver, current_date):
            active.append(waiver)
    return active


def get_waiver_coverage_stats(exemption_map: dict, resources: list, rules: list) -> dict:
    """
    Compute waiver coverage statistics.
    Returns counts of waived vs non-waived rule-resource combinations.
    """
    total_combinations = len(resources) * len(rules)
    waived_count = len(exemption_map)
    non_waived = total_combinations - waived_count

    return {
        "total_rule_resource_pairs": total_combinations,
        "waived_pairs": waived_count,
        "non_waived_pairs": non_waived,
        "waiver_coverage_pct": (waived_count / total_combinations * 100) if total_combinations > 0 else 0.0,
    }


def group_waivers_by_rule(exemption_map: dict) -> dict:
    """Group exemptions by rule ID for reporting."""
    by_rule = {}
    for (resource_id, rule_id), waiver_info in exemption_map.items():
        if rule_id not in by_rule:
            by_rule[rule_id] = []
        by_rule[rule_id].append({
            "resource_id": resource_id,
            "waiver_id": waiver_info["waiver_id"],
            "reason": waiver_info["reason"],
        })
    return by_rule


def validate_waiver_completeness(waivers: list, rules: list) -> list:
    """
    Check for waivers that reference non-existent rules.
    Returns list of invalid waiver IDs.
    """
    rule_ids = {r["id"] for r in rules}
    invalid = []
    for waiver in waivers:
        if waiver["rule_id"] not in rule_ids:
            invalid.append(waiver["id"])
    return invalid
