"""
Report Generator Module
Formats analysis results into the final JSON output structure with summary
statistics, per-test classifications, and aggregate health metrics.
"""

import json


def generate_report(suite_name, classifications, correlation_matrix,
                    timing_baselines, total_tests, total_runs, output_path):
    """
    Generate the final analysis report as a JSON file.

    Args:
        suite_name: Name of the test suite.
        classifications: List of scored classification dicts.
        correlation_matrix: Dict of "test_a:test_b" -> correlation value.
        timing_baselines: Dict of module_name -> timing baseline dict.
        total_tests: Total number of unique tests.
        total_runs: Total number of runs analyzed.
        output_path: File path to write output JSON.

    Returns:
        The report dict (also written to output_path).
    """
    tests_with_failures = sum(
        1 for c in classifications if c["category"] != "healthy"
    )

    health_counts = _compute_health_distribution(classifications, total_tests)

    report = {
        "suite": suite_name,
        "analysis_summary": {
            "total_tests": total_tests,
            "total_runs": total_runs,
            "tests_with_failures": tests_with_failures,
        },
        "classifications": classifications,
        "correlation_matrix": correlation_matrix,
        "timing_baselines": timing_baselines,
        "overall_health": health_counts,
    }

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


def _compute_health_distribution(classifications, total_tests):
    """
    Compute percentage breakdown of test health categories.
    """
    if total_tests == 0:
        return {
            "healthy_pct": 0.0,
            "flaky_pct": 0.0,
            "deterministic_pct": 0.0,
            "env_dependent_pct": 0.0,
        }

    counts = {"healthy": 0, "flaky": 0, "deterministic_bug": 0, "environment_dependent": 0}

    for c in classifications:
        category = c["category"]
        if category in counts:
            counts[category] += 1

    return {
        "healthy_pct": round(counts["healthy"] / total_tests, 4),
        "flaky_pct": round(counts["flaky"] / total_tests, 4),
        "deterministic_pct": round(counts["deterministic_bug"] / total_tests, 4),
        "env_dependent_pct": round(counts["environment_dependent"] / total_tests, 4),
    }


def format_summary_line(report):
    """
    Format a one-line summary for logging purposes.
    """
    summary = report["analysis_summary"]
    health = report["overall_health"]

    return (
        "Suite '{}': {}/{} tests failing | "
        "healthy={:.0%} flaky={:.0%} deterministic={:.0%} env_dependent={:.0%}"
    ).format(
        report["suite"],
        summary["tests_with_failures"],
        summary["total_tests"],
        health["healthy_pct"],
        health["flaky_pct"],
        health["deterministic_pct"],
        health["env_dependent_pct"],
    )
