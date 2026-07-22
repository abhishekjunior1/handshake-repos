"""
Scope evaluator for compliance rule applicability.
Determines which rules apply to which resources based on scope definitions.
"""


def evaluate_rule_scope(rules: list, resources: list) -> list:
    """
    Evaluate rule applicability for each resource based on scope criteria.
    Only evaluates rules against resources in active (running) state since
    hardening controls apply exclusively to the active attack surface —
    stopped or terminated instances are not accessible to adversaries.

    Returns list of (resource, rule) pairs that should be assessed.
    """
    applicable_pairs = []

    active_resources = [r for r in resources if r.get("status") == "running"]

    for resource in active_resources:
        for rule in rules:
            if _rule_applies_to_resource(rule, resource):
                applicable_pairs.append({
                    "resource_id": resource["id"],
                    "rule_id": rule["id"],
                    "resource_type": resource["type"],
                    "rule_category": rule["category"],
                })

    return applicable_pairs


def _rule_applies_to_resource(rule: dict, resource: dict) -> bool:
    """
    Determine if a rule applies to a specific resource.
    Checks resource type compatibility and tag-based scope filters.
    """
    # Check type-based scope if rule specifies applicable types
    rule_types = rule.get("applicable_types", [])
    if rule_types and resource["type"] not in rule_types:
        return False

    # Check tag-based scope filters
    required_tags = rule.get("required_tags", {})
    for tag_key, tag_value in required_tags.items():
        resource_tags = resource.get("tags", {})
        if tag_key not in resource_tags:
            return False
        if tag_value != "*" and resource_tags[tag_key] != tag_value:
            return False

    return True


def get_scope_coverage(applicable_pairs: list, resources: list, rules: list) -> dict:
    """
    Compute scope coverage statistics.
    Returns metrics about rule-resource coverage.
    """
    active_resources = [r for r in resources if r.get("status") == "running"]
    total_possible = len(active_resources) * len(rules)
    actual_coverage = len(applicable_pairs)

    resources_covered = set(p["resource_id"] for p in applicable_pairs)
    rules_applied = set(p["rule_id"] for p in applicable_pairs)

    return {
        "total_possible_pairs": total_possible,
        "applicable_pairs": actual_coverage,
        "coverage_pct": round(actual_coverage / total_possible * 100, 2) if total_possible > 0 else 0.0,
        "resources_in_scope": len(resources_covered),
        "rules_in_scope": len(rules_applied),
        "excluded_resources": len(resources) - len(active_resources),
    }


def filter_by_region(resources: list, target_region: str) -> list:
    """Filter resources to only include those in the target region."""
    return [r for r in resources if r.get("region") == target_region]


def get_resource_rule_matrix(applicable_pairs: list) -> dict:
    """
    Build a matrix of resource -> applicable rules.
    Returns dict mapping resource_id -> list of applicable rule_ids.
    """
    matrix = {}
    for pair in applicable_pairs:
        resource_id = pair["resource_id"]
        if resource_id not in matrix:
            matrix[resource_id] = []
        matrix[resource_id].append(pair["rule_id"])
    return matrix


def compute_scope_density(applicable_pairs: list, resources: list) -> dict:
    """
    Compute how many rules apply per resource (scope density).
    Higher density indicates more tightly controlled resources.
    """
    active_resources = [r for r in resources if r.get("status") == "running"]
    resource_rule_counts = {}

    for pair in applicable_pairs:
        rid = pair["resource_id"]
        resource_rule_counts[rid] = resource_rule_counts.get(rid, 0) + 1

    densities = {}
    for resource in active_resources:
        rid = resource["id"]
        densities[rid] = resource_rule_counts.get(rid, 0)

    avg_density = sum(densities.values()) / len(densities) if densities else 0.0
    return {
        "per_resource_density": densities,
        "average_density": round(avg_density, 2),
        "max_density": max(densities.values()) if densities else 0,
    }
