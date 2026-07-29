"""
Timing Analyzer Module
Computes timing statistics per test and per module: mean, stddev, coefficient
of variation, and identifies outlier runs based on z-score thresholds.
"""

import math
from collections import defaultdict


def compute_timing_stats(runs, test_ids, weighted_vectors, decay_factor):
    """
    Compute timing statistics for each test across all runs.

    Args:
        runs: List of run dicts with results.
        test_ids: List of test IDs to analyze.
        weighted_vectors: Dict mapping test_id -> weighted failure vector
                         (used for weighting recent timing observations).
        decay_factor: Temporal decay for weighting recent runs.

    Returns:
        Dict mapping test_id -> timing stats dict.
    """
    test_durations = defaultdict(list)

    for run in runs:
        for result in run["results"]:
            if result["test_id"] in test_ids:
                test_durations[result["test_id"]].append(result["duration_ms"])

    timing_stats = {}
    for tid in test_ids:
        durations = test_durations.get(tid, [])
        if not durations:
            timing_stats[tid] = _empty_stats()
            continue

        stats = _compute_weighted_stats(durations, decay_factor)
        stats["outlier_runs"] = _detect_outliers(durations, stats["mean_ms"], stats["stddev_ms"])
        stats["sample_count"] = len(durations)
        timing_stats[tid] = stats

    return timing_stats


def compute_module_baselines(runs, test_module_map):
    """
    Compute timing baselines per module.

    Args:
        runs: List of run dicts.
        test_module_map: Dict mapping test_id -> module_name.

    Returns:
        Dict mapping module_name -> {"mean_ms": float, "stddev_ms": float}.
    """
    module_durations = defaultdict(list)

    for run in runs:
        for result in run["results"]:
            tid = result["test_id"]
            module = test_module_map.get(tid, "default")
            module_durations[module].append(result["duration_ms"])

    baselines = {}
    for module, durations in module_durations.items():
        if not durations:
            baselines[module] = {"mean_ms": 0.0, "stddev_ms": 0.0}
            continue

        mean = sum(durations) / len(durations)
        variance = sum((d - mean) ** 2 for d in durations) / len(durations)
        stddev = math.sqrt(variance)
        baselines[module] = {"mean_ms": round(mean, 3), "stddev_ms": round(stddev, 3)}

    return baselines


def compute_global_baseline(runs):
    """
    Compute a single global timing baseline across all tests and runs.

    Args:
        runs: List of run dicts.

    Returns:
        Dict with "mean_ms" and "stddev_ms".
    """
    all_durations = []
    for run in runs:
        for result in run["results"]:
            all_durations.append(result["duration_ms"])

    if not all_durations:
        return {"mean_ms": 0.0, "stddev_ms": 0.0}

    mean = sum(all_durations) / len(all_durations)
    variance = sum((d - mean) ** 2 for d in all_durations) / len(all_durations)
    stddev = math.sqrt(variance)

    return {"mean_ms": round(mean, 3), "stddev_ms": round(stddev, 3)}


def check_timing_anomaly(test_timing_stats, baseline, cv_threshold):
    """
    Determine if a test has anomalous timing relative to a baseline.

    Args:
        test_timing_stats: Stats dict for a single test.
        baseline: Baseline dict with mean_ms and stddev_ms.
        cv_threshold: Coefficient of variation threshold.

    Returns:
        Boolean indicating timing anomaly.
    """
    if test_timing_stats["sample_count"] < 2:
        return False

    cv = test_timing_stats["cv"]
    if cv > cv_threshold:
        return True

    # Check if test mean deviates significantly from baseline
    test_mean = test_timing_stats["mean_ms"]
    baseline_mean = baseline["mean_ms"]
    baseline_stddev = baseline["stddev_ms"]

    if baseline_stddev == 0:
        return False

    z_score = abs(test_mean - baseline_mean) / baseline_stddev
    return z_score > 2.0


def _compute_weighted_stats(durations, decay_factor):
    """Compute decay-weighted timing statistics."""
    n = len(durations)
    weights = [decay_factor ** (n - 1 - i) for i in range(n)]
    total_weight = sum(weights)

    weighted_mean = sum(d * w for d, w in zip(durations, weights)) / total_weight
    weighted_variance = sum(w * (d - weighted_mean) ** 2 for d, w in zip(durations, weights)) / total_weight
    weighted_stddev = math.sqrt(weighted_variance)

    cv = weighted_stddev / weighted_mean if weighted_mean > 0 else 0.0

    return {
        "mean_ms": round(weighted_mean, 3),
        "stddev_ms": round(weighted_stddev, 3),
        "cv": round(cv, 4),
        "min_ms": round(min(durations), 3),
        "max_ms": round(max(durations), 3),
    }


def _detect_outliers(durations, mean, stddev):
    """Detect outlier indices using z-score > 2."""
    if stddev == 0:
        return []

    outliers = []
    for i, d in enumerate(durations):
        z = abs(d - mean) / stddev
        if z > 2.0:
            outliers.append(i)

    return outliers


def _empty_stats():
    """Return empty stats for tests with no timing data."""
    return {
        "mean_ms": 0.0,
        "stddev_ms": 0.0,
        "cv": 0.0,
        "min_ms": 0.0,
        "max_ms": 0.0,
        "outlier_runs": [],
        "sample_count": 0,
    }
