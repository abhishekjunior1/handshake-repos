"""
Flakiness Detector Module
Computes flip rates (pass→fail and fail→pass transitions), windowed failure
rates, and trend analysis to identify test instability patterns.
"""

import math


def analyze(binary_vectors, test_ids, window_size, total_runs):
    """
    Analyze flakiness metrics for specified tests.

    Args:
        binary_vectors: Dict mapping test_id -> list of 0/1 values per run.
        test_ids: List of test IDs to analyze.
        window_size: Number of runs per analysis window.
        total_runs: Total number of runs in dataset.

    Returns:
        Dict mapping test_id -> flakiness metrics dict.
    """
    results = {}

    for tid in test_ids:
        vector = binary_vectors.get(tid, [])
        if not vector:
            results[tid] = _empty_metrics()
            continue

        flip_rate = _compute_flip_rate(vector)
        windowed_rates = _compute_windowed_rates(vector, window_size)
        trend = _compute_trend(windowed_rates)
        cumulative_rate = sum(vector) / len(vector) if vector else 0.0
        recent_rate = windowed_rates[-1] if windowed_rates else cumulative_rate

        results[tid] = {
            "flip_rate": round(flip_rate, 4),
            "cumulative_failure_rate": round(cumulative_rate, 4),
            "recent_failure_rate": round(recent_rate, 4),
            "windowed_rates": [round(r, 4) for r in windowed_rates],
            "trend": trend,
            "total_flips": _count_flips(vector),
            "longest_failure_streak": _longest_streak(vector, 1),
            "longest_pass_streak": _longest_streak(vector, 0),
        }

    return results


def _compute_flip_rate(vector):
    """
    Compute flip rate: proportion of adjacent run pairs where outcome changes.
    Range: 0 (perfectly stable) to 1 (alternates every run).
    """
    if len(vector) < 2:
        return 0.0

    flips = 0
    for i in range(1, len(vector)):
        if vector[i] != vector[i - 1]:
            flips += 1

    return flips / (len(vector) - 1)


def _count_flips(vector):
    """Count total number of status transitions."""
    if len(vector) < 2:
        return 0

    return sum(1 for i in range(1, len(vector)) if vector[i] != vector[i - 1])


def _compute_windowed_rates(vector, window_size):
    """
    Compute failure rate for each non-overlapping window of runs.
    Last window may be smaller if total runs don't divide evenly.
    """
    if not vector:
        return []

    windows = []
    for start in range(0, len(vector), window_size):
        window = vector[start:start + window_size]
        rate = sum(window) / len(window)
        windows.append(rate)

    return windows


def _compute_trend(windowed_rates):
    """
    Determine trend direction using linear regression slope.
    Returns 'increasing', 'decreasing', or 'stable'.
    """
    if len(windowed_rates) < 2:
        return "stable"

    n = len(windowed_rates)
    x_vals = list(range(n))
    x_mean = sum(x_vals) / n
    y_mean = sum(windowed_rates) / n

    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_vals, windowed_rates))
    denominator = sum((x - x_mean) ** 2 for x in x_vals)

    if denominator == 0:
        return "stable"

    slope = numerator / denominator

    # Threshold for meaningful trend (> 5% change per window)
    if slope > 0.05:
        return "increasing"
    elif slope < -0.05:
        return "decreasing"
    else:
        return "stable"


def _longest_streak(vector, value):
    """Find the longest consecutive sequence of a given value."""
    max_streak = 0
    current_streak = 0

    for v in vector:
        if v == value:
            current_streak += 1
            max_streak = max(max_streak, current_streak)
        else:
            current_streak = 0

    return max_streak


def compute_flakiness_score(metrics):
    """
    Compute a composite flakiness score from multiple signals.
    Higher score = more likely flaky.

    Args:
        metrics: Flakiness metrics dict for a single test.

    Returns:
        Float score in [0, 1].
    """
    flip_weight = 0.4
    rate_variance_weight = 0.3
    trend_weight = 0.3

    flip_score = min(metrics["flip_rate"] * 2, 1.0)

    rates = metrics["windowed_rates"]
    if len(rates) > 1:
        rate_mean = sum(rates) / len(rates)
        rate_variance = sum((r - rate_mean) ** 2 for r in rates) / len(rates)
        variance_score = min(math.sqrt(rate_variance) * 2, 1.0)
    else:
        variance_score = 0.0

    trend_score = 0.5 if metrics["trend"] == "stable" else 0.3
    if metrics["trend"] == "increasing" or metrics["trend"] == "decreasing":
        trend_score = 0.7

    score = (flip_weight * flip_score +
             rate_variance_weight * variance_score +
             trend_weight * trend_score)

    return round(min(score, 1.0), 4)


def _empty_metrics():
    """Return empty metrics for tests with no data."""
    return {
        "flip_rate": 0.0,
        "cumulative_failure_rate": 0.0,
        "recent_failure_rate": 0.0,
        "windowed_rates": [],
        "trend": "stable",
        "total_flips": 0,
        "longest_failure_streak": 0,
        "longest_pass_streak": 0,
    }
