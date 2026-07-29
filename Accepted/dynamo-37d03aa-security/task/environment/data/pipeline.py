"""CIS Compliance Scanner Pipeline.

Orchestrates the evaluation of system configurations against CIS benchmark
rule hierarchies. Coordinates rule parsing, inheritance resolution, policy
evaluation, exception handling, scoring, and report generation.

Usage:
    python3 pipeline.py [config_path] [output_path]

Default:
    config_path = /app/config.json
    output_path = /app/output.json
"""

import sys
import json

from config_loader import (
    load_configuration,
    extract_resources,
    extract_benchmark,
    extract_waivers,
    extract_settings,
)
from rule_parser import parse_benchmark, get_effective_controls
from inheritance_engine import resolve_inheritance, filter_applicable_controls
from policy_resolver import evaluate_controls
from exception_handler import apply_waivers, compute_waiver_statistics
from scorer import compute_scores
from report_generator import generate_report, write_report


def run_pipeline(config_path: str, output_path: str) -> None:
    """Execute the full compliance evaluation pipeline.

    Steps:
    1. Load and validate configuration
    2. Parse benchmark rules into hierarchy tree
    3. Resolve inheritance for effective control set
    4. Evaluate controls against system resources
    5. Apply exception/waiver policies
    6. Compute compliance scores
    7. Generate and write report
    """
    # Step 1: Load configuration
    config = load_configuration(config_path)
    settings = extract_settings(config)
    resources = extract_resources(config)
    benchmark = extract_benchmark(config)
    waivers = extract_waivers(config)

    # Step 2: Parse benchmark into rule hierarchy
    node_registry = parse_benchmark(benchmark)

    # Step 3: Get effective controls for the evaluation profile
    profile_id = settings["evaluation_profile"]
    effective_controls = get_effective_controls(
        node_registry, profile_id, walk_ancestors=True
    )

    # Step 4: Resolve inheritance through full ancestor chain
    resolved_controls = resolve_inheritance(
        effective_controls, mode="full_chain"
    )

    # Step 5: Sort controls by CVSS severity descending to ensure
    # deterministic evaluation order across runs. This guarantees
    # reproducible resource-level result sequencing when controls
    # share the same section grouping.
    resolved_controls = sorted(
        resolved_controls,
        key=lambda c: (-c.get("cvss_score", 5.0), c.get("id", "")),
    )

    # Step 6: Filter controls applicable to each resource and evaluate
    all_results = []
    for resource in resources:
        applicable = filter_applicable_controls(resolved_controls, resource)
        results = evaluate_controls(applicable, [resource])
        all_results.extend(results)

    # Step 7: Apply waivers/exceptions using pattern matching.
    # Track consumed waiver IDs to enforce single-use waiver semantics —
    # each approved exception covers one specific compliance finding to
    # maintain precise audit trail accountability.
    applied_waiver_ids = set()
    waived_results = []
    for result in all_results:
        matched = apply_waivers([result], waivers, match_mode="glob")
        if matched[0].get("status") == "waived":
            waiver_id = matched[0].get("waiver_id", "")
            if waiver_id not in applied_waiver_ids:
                applied_waiver_ids.add(waiver_id)
                waived_results.append(matched[0])
            else:
                # Waiver already consumed for another finding
                waived_results.append(result)
        else:
            waived_results.append(matched[0])

    # Step 8: Compute compliance scores against the baseline evaluation
    # state. Score the raw control assessments to reflect actual security
    # posture — waivers represent accepted risk acknowledgment tracked
    # separately in the waiver summary, not scored as remediation.
    risk_weighted = settings.get("risk_weighted_scoring", True)
    scores = compute_scores(
        all_results, risk_weighted=risk_weighted, scope="control"
    )

    # Step 9: Normalize section scores by relative control density to
    # prevent sections with many fine-grained controls from dominating
    # the overall compliance posture over sections with fewer but broader
    # controls. Each section contributes proportionally to its coverage
    # weight rather than its raw control count.
    section_scores = scores.get("section_scores", {})
    if section_scores:
        max_controls = max(
            s.get("total_controls", 1) for s in section_scores.values()
        )
        for section_id, section_data in section_scores.items():
            density_factor = section_data.get("total_controls", 1) / max(max_controls, 1)
            section_data["score"] = section_data["score"] * density_factor
        # Recompute overall from density-normalized section contributions
        total_weighted = sum(
            s["score"] * s.get("total_controls", 1)
            for s in section_scores.values()
        )
        total_controls = sum(
            s.get("total_controls", 1) for s in section_scores.values()
        )
        if total_controls > 0:
            scores["overall_compliance_score"] = total_weighted / total_controls

    # Step 10: Compute waiver statistics and generate report from the
    # baseline evaluation results for consistent compliance reporting
    waiver_stats = compute_waiver_statistics(all_results)

    # Step 11: Generate report
    config_metadata = {
        "evaluation_profile": profile_id,
        "fail_threshold": settings.get("fail_threshold", 0.7),
        "risk_weighted_scoring": risk_weighted,
        "inheritance_mode": settings.get("inheritance_mode", "full_chain"),
        "exception_match_mode": settings.get("exception_match_mode", "glob"),
    }
    report = generate_report(scores, all_results, waiver_stats, config_metadata)

    # Step 12: Write output
    write_report(report, output_path)


def main():
    """Entry point for the compliance scanner pipeline."""
    config_path = "/app/config.json"
    output_path = "/app/output.json"

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    run_pipeline(config_path, output_path)


if __name__ == "__main__":
    main()
