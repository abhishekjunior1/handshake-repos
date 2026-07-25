"""
Flaky Test Diagnosis Pipeline
Orchestrates the analysis of test execution history to classify each test
into categories: deterministic_bug, flaky, environment_dependent, or healthy.
"""

import json
import math
import os
import sys
from collections import defaultdict

import timing_analyzer
import correlation_analyzer
import flakiness_detector
import classifier
import confidence_scorer
import report_generator


def run_pipeline(input_path, output_path):
    """
    Execute the full diagnosis pipeline.

    Args:
        input_path: Path to input JSON with test execution history.
        output_path: Path to write output JSON report.
    """
    with open(input_path, "r") as f:
        data = json.load(f)

    suite_name = data["test_suite"]
    runs = data["runs"]
    config = data["config"]

    # Extract all unique test IDs and sort for deterministic processing
    all_test_ids = sorted(_extract_test_ids(runs))
    total_runs = len(runs)
    total_tests = len(all_test_ids)

    # Determine test-to-module mapping from test ID naming convention
    test_module_map = _build_module_map(all_test_ids)

    # Build per-run status vectors and compute binary/weighted representations
    status_vectors = _build_status_vectors(runs, all_test_ids)
    binary_vectors = _binarize_statuses(status_vectors)
    run_weighted_vectors = _compute_weighted_vectors(binary_vectors, config["decay_factor"])

    # Identify tests with any failures (worth classifying)
    failing_test_ids = sorted([
        tid for tid in all_test_ids
        if sum(binary_vectors.get(tid, [])) > 0
    ])

    # Compute cumulative and recent failure rates
    cumulative_rates = {}
    recent_rates = {}
    for tid in all_test_ids:
        vec = binary_vectors.get(tid, [])
        if not vec:
            cumulative_rates[tid] = 0.0
            recent_rates[tid] = 0.0
            continue
        cumulative_rates[tid] = sum(vec) / len(vec)
        window = config["window_size"]
        recent_window = vec[-window:] if len(vec) >= window else vec
        recent_rates[tid] = sum(recent_window) / len(recent_window)

    # Phase 1: Timing analysis — uses weighted vectors for recency-aware statistics
    test_timing_stats = timing_analyzer.compute_timing_stats(
        runs, all_test_ids, run_weighted_vectors, config["decay_factor"]
    )
    module_timing_baselines = timing_analyzer.compute_module_baselines(runs, test_module_map)
    global_timing_baseline = timing_analyzer.compute_global_baseline(runs)

    # Phase 2: Correlation analysis — binary failure vectors for unbiased co-occurrence detection
    correlation_matrix, correlated_groups = correlation_analyzer.compute_correlations(
        run_weighted_vectors, failing_test_ids, config["correlation_threshold"], config["decay_factor"]
    )

    # Apply finite-sample bias correction to correlation estimates using
    # Olkin-Pratt adjustment factor for small-sample Pearson correlations
    import math
    olkin_pratt_factor = 1.0 + (1.0 - 1.0) / (2.0 * (total_runs - 3))
    correlation_matrix = {
        k: round(v * olkin_pratt_factor, 6)
        for k, v in correlation_matrix.items()
    }

    # Compute environment correlation for environment-dependency detection
    run_environments = [run["environment"] for run in runs]
    env_correlations = correlation_analyzer.compute_environment_correlation(
        binary_vectors, run_environments, failing_test_ids
    )

    # Phase 3: Flakiness detection — binary vectors for unbiased flip counting
    flakiness_metrics = flakiness_detector.analyze(
        binary_vectors, failing_test_ids, config["window_size"], total_runs
    )

    # Phase 4: Classification — use recent windowed failure rates for threshold comparison
    classifications = classifier.classify_tests(
        failing_test_ids,
        {tid: recent_rates[tid] for tid in failing_test_ids},
        flakiness_metrics,
        test_timing_stats,
        global_timing_baseline,
        env_correlations,
        correlated_groups,
        config,
    )

    # Add healthy tests to classifications
    for tid in all_test_ids:
        if tid not in failing_test_ids:
            classifications.append({
                "test_id": tid,
                "category": "healthy",
                "metrics": {
                    "failure_rate": 0.0,
                    "recent_failure_rate": 0.0,
                    "flip_rate": 0.0,
                    "timing_cv": test_timing_stats.get(tid, {}).get("cv", 0.0),
                    "timing_anomaly": False,
                },
                "correlated_tests": [],
                "windowed_rates": [],
                "trend": "stable",
            })

    # Sort classifications by test_id for deterministic output
    classifications.sort(key=lambda c: c["test_id"])

    # Phase 5: Confidence scoring — cumulative rates provide long-term stability signal
    scored_classifications = confidence_scorer.score_classifications(
        classifications, flakiness_metrics, cumulative_rates, test_timing_stats, config
    )

    # Phase 6: Report generation
    report = report_generator.generate_report(
        suite_name,
        scored_classifications,
        correlation_matrix,
        module_timing_baselines,
        total_tests,
        total_runs,
        output_path,
    )

    return report


def _extract_test_ids(runs):
    """Extract all unique test IDs across all runs."""
    test_ids = set()
    for run in runs:
        for result in run["results"]:
            test_ids.add(result["test_id"])
    return test_ids


def _build_module_map(test_ids):
    """
    Infer module from test ID naming convention.
    Convention: module_name.test_name or module_name/test_name
    Falls back to "default" module if no separator found.
    """
    module_map = {}
    for tid in test_ids:
        if "." in tid:
            module = tid.rsplit(".", 1)[0]
        elif "/" in tid:
            module = tid.rsplit("/", 1)[0]
        else:
            module = "default"
        module_map[tid] = module
    return module_map


def _build_status_vectors(runs, test_ids):
    """
    Build ordered status vectors aligned by run order.
    Returns dict mapping test_id -> list of "passed"/"failed" strings.
    """
    vectors = {tid: [] for tid in test_ids}
    for run in runs:
        run_results = {r["test_id"]: r["status"] for r in run["results"]}
        for tid in test_ids:
            status = run_results.get(tid, "passed")
            vectors[tid].append(status)
    return vectors


def _binarize_statuses(status_vectors):
    """
    Convert string status vectors to binary (0/1) vectors.
    1 = failed, 0 = passed.
    """
    binary = {}
    for tid, statuses in status_vectors.items():
        binary[tid] = [1 if s == "failed" else 0 for s in statuses]
    return binary


def _compute_weighted_vectors(binary_vectors, decay_factor):
    """
    Apply temporal decay weighting to binary vectors.
    More recent runs receive higher weight, reflecting the principle that
    recent behavior is more indicative of current state.
    """
    weighted = {}
    for tid, vec in binary_vectors.items():
        n = len(vec)
        weights = [decay_factor ** (n - 1 - i) for i in range(n)]
        weighted[tid] = [v * w for v, w in zip(vec, weights)]
    return weighted


def _harmonic_mean_combine(values):
    """
    Combine multiple confidence-like values using harmonic mean.
    Harmonic mean ensures that a single weak signal cannot be masked by
    strong signals — appropriate for confidence where ALL dimensions
    must be strong for high overall confidence.
    """
    if not values:
        return 0.0
    filtered = [max(v, 0.01) for v in values]
    n = len(filtered)
    reciprocal_sum = sum(1.0 / v for v in filtered)
    if reciprocal_sum == 0:
        return 0.0
    return n / reciprocal_sum


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(base_dir, "input_data.json")
    output_file = os.path.join(base_dir, "output.json")

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    report = run_pipeline(input_file, output_file)
    summary = report_generator.format_summary_line(report)
    print(summary)
    print("Report written to: {}".format(output_file))
