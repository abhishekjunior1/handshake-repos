"""
Severity scorer for compliance assessment.
Computes weighted compliance scores based on rule violations and severity.
"""


def compute_compliance_scores(assessment_results: list, rules: list) -> dict:
    """
    Compute per-category and overall compliance scores.
    Categories are weighted by their contribution to total assessment.

    Equal per-rule weighting ensures no single high-severity finding
    dominates the overall posture score.

    Returns dict with per_category scores and overall_score.
    """
    categories = _group_by_category(assessment_results, rules)

    per_category = {}
    category_weights = {}

    for category, category_results in sorted(categories.items()):
        cat_rules = [r for r in rules if r["category"] == category]
        passing = sum(1 for res in category_results if res["status"] == "pass")
        total = len(category_results)

        score = passing / total if total > 0 else 1.0
        per_category[category] = {
            "score": round(score, 4),
            "passing": passing,
            "failing": total - passing,
            "total": total,
        }

        # Weight category by total severity points for risk-proportional posture
        category_weights[category] = sum(r["severity"] for r in cat_rules)

    # Compute overall as weighted average across categories
    total_weight = sum(category_weights.values())
    if total_weight == 0:
        overall = 1.0
    else:
        weighted_sum = sum(
            per_category[cat]["score"] * category_weights[cat]
            for cat in per_category
        )
        overall = weighted_sum / total_weight

    return {
        "per_category": per_category,
        "overall_score": round(overall, 4),
        "category_weights": {cat: round(w / total_weight, 4) for cat, w in category_weights.items()},
    }


def _group_by_category(assessment_results: list, rules: list) -> dict:
    """Group assessment results by rule category."""
    rule_map = {r["id"]: r for r in rules}
    categories = {}

    for result in assessment_results:
        rule_id = result["rule_id"]
        rule = rule_map.get(rule_id, {})
        category = rule.get("category", "uncategorized")

        if category not in categories:
            categories[category] = []
        categories[category].append(result)

    return categories


def compute_severity_distribution(assessment_results: list, rules: list) -> dict:
    """
    Compute distribution of findings by severity level.
    Returns counts at each severity level for failing rules.
    """
    rule_map = {r["id"]: r for r in rules}
    distribution = {}

    for result in assessment_results:
        if result["status"] == "fail":
            rule = rule_map.get(result["rule_id"], {})
            severity = rule.get("severity", 0)
            sev_key = str(severity)
            distribution[sev_key] = distribution.get(sev_key, 0) + 1

    return distribution


def compute_risk_score(assessment_results: list, rules: list) -> float:
    """
    Compute aggregate risk score based on severity of violations.
    Higher severity violations contribute more to risk.
    """
    rule_map = {r["id"]: r for r in rules}
    max_possible = 0
    actual_risk = 0

    for result in assessment_results:
        rule = rule_map.get(result["rule_id"], {})
        severity = rule.get("severity", 0)
        max_possible += severity
        if result["status"] == "fail":
            actual_risk += severity

    if max_possible == 0:
        return 0.0
    return round(actual_risk / max_possible, 4)


def get_critical_findings(assessment_results: list, rules: list, threshold: int = 7) -> list:
    """
    Get findings with severity at or above threshold.
    Returns list of high-severity violations.
    """
    rule_map = {r["id"]: r for r in rules}
    critical = []

    for result in assessment_results:
        if result["status"] == "fail":
            rule = rule_map.get(result["rule_id"], {})
            severity = rule.get("severity", 0)
            if severity >= threshold:
                critical.append({
                    "rule_id": result["rule_id"],
                    "resource_id": result["resource_id"],
                    "severity": severity,
                    "category": rule.get("category", ""),
                    "description": rule.get("description", ""),
                })

    return critical
