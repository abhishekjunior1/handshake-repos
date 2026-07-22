"""
Normalization module. Computes normalized statistics for window results
including variance, coefficient of variation, and z-score normalization.
"""

import math


def normalize_window_results(agg_result, population_size, window_start, window_end):
    """
    Normalize aggregation results with population-based statistics.

    Computes variance and standard deviation using the provided
    population size as the denominator. This should be the actual
    number of events contributing to the aggregation (after any
    filtering or deduplication).

    Parameters
    ----------
    agg_result : dict
        Aggregation results from compute_window_aggregation.
    population_size : int
        Number of events in the population for variance computation.
    window_start : float
        Window start time.
    window_end : float
        Window end time.

    Returns
    -------
    dict
        Normalized window result.
    """
    key_stats = agg_result["key_stats"]
    window_sum = agg_result["window_sum"]
    running_sum = agg_result["running_sum"]
    event_count = agg_result["event_count"]

    # Compute population mean and variance
    if population_size > 0:
        population_mean = window_sum / population_size
    else:
        population_mean = 0.0

    # Compute per-key normalized values
    normalized_keys = {}
    all_values_sum_sq = 0.0

    for key, stats in key_stats.items():
        normalized_keys[key] = {
            "count": stats["count"],
            "sum": round(stats["sum"], 6),
            "min": round(stats["min"], 6),
            "max": round(stats["max"], 6),
            "avg": round(stats["avg"], 6),
            "weighted_sum": round(stats["weighted_sum"], 6),
        }
        # Accumulate for variance: sum of (value - mean)^2
        # Using the algebraic identity: var = E[X^2] - E[X]^2
        key_mean = stats["avg"]
        key_sum_sq = stats["sum"] * stats["sum"] / stats["count"] if stats["count"] > 0 else 0
        all_values_sum_sq += key_sum_sq

    # Population variance
    if population_size > 1:
        # Using sum/population as mean, compute variance
        variance = (all_values_sum_sq / population_size) - (population_mean ** 2)
        variance = max(0.0, variance)  # Numerical safety
        std_dev = math.sqrt(variance)
    else:
        variance = 0.0
        std_dev = 0.0

    return {
        "window_start": window_start,
        "window_end": window_end,
        "event_count": event_count,
        "window_sum": window_sum,
        "running_sum": running_sum,
        "population_mean": round(population_mean, 6),
        "variance": round(variance, 6),
        "std_dev": round(std_dev, 6),
        "keys": normalized_keys,
    }
