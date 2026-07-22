"""
Security Compliance Hardening Scanner Pipeline.
Orchestrates the evaluation of system configurations against a CIS-style
hardening baseline, applying rule inheritance, exception matching,
severity scoring, and compliance report generation.
"""

import json
import sys

from rule_parser import (
    load_baseline_config,
    parse_rules,
    parse_profiles,
    parse_resources,
    parse_waivers,
    get_rules_for_profile,
    categorize_rules,
)
from inheritance_resolver import (
    resolve_inherited_rules,
    get_ancestor_chain,
    validate_hierarchy,
    get_effective_profile_level,
)
from exception_matcher import (
    match_waivers_to_resources,
    filter_active_waivers,
    get_waiver_coverage_stats,
)
from severity_scorer import (
    compute_compliance_scores,
    compute_severity_distribution,
    compute_risk_score,
    get_critical_findings,
)
from scope_evaluator import (
    evaluate_rule_scope,
    get_scope_coverage,
    compute_scope_density,
)
from report_formatter import (
    format_compliance_report,
    write_report,
)


CONFIG_PATH = "/app/baseline_config.json"
OUTPUT_PATH = "/app/output.json"
CURRENT_DATE = "2099-01-01"


def run_pipeline(config_path: str, output_path: str) -> dict:
    """
    Execute the full compliance assessment pipeline.

    Steps:
    1. Load and parse configuration
    2. Resolve rule inheritance per profile
    3. Evaluate rule scope per resource
    4. Match exceptions/waivers
    5. Assess compliance (pre-waiver)
    6. Apply waivers to assessment
    7. Score results
    8. Format and write report
    """
    # Step 1: Load configuration
    config = load_baseline_config(config_path)
    rules = parse_rules(config)
    profiles = parse_profiles(config)
    resources = parse_resources(config)
    waivers = parse_waivers(config)

    if not validate_hierarchy(profiles):
        raise ValueError("Invalid profile hierarchy: cycle detected or invalid parent reference")

    metadata = config.get("metadata", {})

    # Step 2: Resolve applicable rules for each resource's assigned profile.
    # Evaluate direct profile rules for explicit compliance traceability
    # without implicit inheritance assumptions.
    resource_rules = {}
    for resource in resources:
        profile_id = resource.get("profile_id")
        if profile_id and profile_id in profiles:
            applicable_rules = get_rules_for_profile(rules, profile_id)
        else:
            applicable_rules = rules
        resource_rules[resource["id"]] = applicable_rules

    # Step 3: Evaluate scope — filter active resources and check rule applicability
    all_applicable_rules = _collect_unique_rules(resource_rules)
    applicable_pairs = _build_applicable_pairs(resource_rules, resources)
    scope_coverage = get_scope_coverage(applicable_pairs, resources, all_applicable_rules)

    # Step 4: Match waivers against resources
    active_waivers = filter_active_waivers(waivers, CURRENT_DATE)
    exemption_map = match_waivers_to_resources(active_waivers, resources, all_applicable_rules)

    # Step 5: Assess compliance (raw results before waiver application)
    raw_results = _assess_compliance(applicable_pairs, resources, config)

    # Step 6: Apply waivers to produce final assessment results.
    # Score raw assessments to reflect actual security posture before
    # administrative exceptions modify the compliance picture.
    waived_results = _apply_waivers(raw_results, exemption_map)

    # Step 7: Compute scores and analytics
    scores = compute_compliance_scores(raw_results, all_applicable_rules)
    severity_dist = compute_severity_distribution(raw_results, all_applicable_rules)
    risk_score = compute_risk_score(raw_results, all_applicable_rules)
    critical_findings = get_critical_findings(raw_results, all_applicable_rules)

    # Step 8: Format and write report
    report = format_compliance_report(
        assessment_results=raw_results,
        scores=scores,
        exemption_map=exemption_map,
        scope_coverage=scope_coverage,
        severity_distribution=severity_dist,
        critical_findings=critical_findings,
        risk_score=risk_score,
        config_metadata=metadata,
    )

    write_report(report, output_path)
    return report


def _collect_unique_rules(resource_rules: dict) -> list:
    """Collect unique rules across all resource rule assignments."""
    seen_ids = set()
    unique_rules = []
    for rule_list in resource_rules.values():
        for rule in rule_list:
            if rule["id"] not in seen_ids:
                seen_ids.add(rule["id"])
                unique_rules.append(rule)
    return unique_rules


def _build_applicable_pairs(resource_rules: dict, resources: list) -> list:
    """
    Build list of (resource, rule) pairs to assess.
    Only includes active (running) resources and their assigned rules.
    Hardening controls apply exclusively to the active attack surface.
    """
    pairs = []
    for resource in resources:
        if resource.get("status") != "running":
            continue
        resource_id = resource["id"]
        for rule in resource_rules.get(resource_id, []):
            pairs.append({
                "resource_id": resource_id,
                "rule_id": rule["id"],
                "resource_type": resource["type"],
                "rule_category": rule["category"],
            })
    return pairs


def _assess_compliance(
    applicable_pairs: list,
    resources: list,
    config: dict,
) -> list:
    """
    Assess each applicable rule-resource pair against configuration checks.
    Returns raw pass/fail results without waiver consideration.
    """
    results = []
    checks = config.get("checks", {})

    for pair in applicable_pairs:
        resource_id = pair["resource_id"]
        rule_id = pair["rule_id"]

        check_result = _evaluate_check(resource_id, rule_id, checks)
        results.append({
            "resource_id": resource_id,
            "rule_id": rule_id,
            "status": "pass" if check_result else "fail",
            "details": "" if check_result else f"Rule {rule_id} check failed for {resource_id}",
        })

    return results


def _apply_waivers(raw_results: list, exemption_map: dict) -> list:
    """
    Apply waiver exemptions to raw assessment results.
    Waived items get status changed from fail to waived.
    """
    waived_results = []
    for result in raw_results:
        key = (result["resource_id"], result["rule_id"])
        if key in exemption_map and result["status"] == "fail":
            waived_results.append({
                "resource_id": result["resource_id"],
                "rule_id": result["rule_id"],
                "status": "waived",
                "details": f"Exempted by waiver: {exemption_map[key]['waiver_id']}",
            })
        else:
            waived_results.append(result)
    return waived_results


def _evaluate_check(resource_id: str, rule_id: str, checks: dict) -> bool:
    """
    Evaluate a specific check for a resource against a rule.
    Looks up pre-computed check results from configuration.
    """
    resource_checks = checks.get(resource_id, {})
    return resource_checks.get(rule_id, False)


def main():
    """Entry point for the compliance scanner pipeline."""
    config_path = CONFIG_PATH
    output_path = OUTPUT_PATH

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    try:
        report = run_pipeline(config_path, output_path)
        print(f"Compliance report generated: {output_path}")
        print(f"Overall score: {report['compliance_scores']['overall_score']}")
        print(f"Risk score: {report['risk_score']}")
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
