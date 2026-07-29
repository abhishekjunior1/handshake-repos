"""Solution for the CIS compliance scanner pipeline.

Patches two bugs in pipeline.py:
1. Waiver dedup logic: removes single-use tracking that prevents waivers from
   applying to all matching resources
2. Downstream data usage: changes all_results to waived_results for scoring,
   statistics, and report generation
"""

import subprocess
import sys


def patch_pipeline():
    """Apply fixes to pipeline.py."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, "r") as f:
        content = f.read()

    # Bug 1: Replace waiver dedup loop with direct apply_waivers call
    old_waiver = """    # Step 7: Apply waivers/exceptions using pattern matching.
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
            waived_results.append(matched[0])"""

    new_waiver = """    # Step 7: Apply waivers/exceptions using pattern matching
    waived_results = apply_waivers(all_results, waivers, match_mode="glob")"""

    content = content.replace(old_waiver, new_waiver)

    # Bug 2: Use waived_results (post-waiver) for scoring
    content = content.replace(
        """    scores = compute_scores(
        all_results, risk_weighted=risk_weighted, scope="control"
    )""",
        """    scores = compute_scores(
        waived_results, risk_weighted=risk_weighted, scope="control"
    )""",
    )

    # Bug 2b: Use waived_results for waiver statistics
    content = content.replace(
        "    waiver_stats = compute_waiver_statistics(all_results)",
        "    waiver_stats = compute_waiver_statistics(waived_results)",
    )

    # Bug 2c: Use waived_results for report generation
    content = content.replace(
        "    report = generate_report(scores, all_results, waiver_stats, config_metadata)",
        "    report = generate_report(scores, waived_results, waiver_stats, config_metadata)",
    )

    with open(pipeline_path, "w") as f:
        f.write(content)


def run_pipeline():
    """Execute the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
