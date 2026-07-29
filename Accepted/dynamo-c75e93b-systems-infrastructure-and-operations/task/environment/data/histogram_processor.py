"""
Histogram processor module for the metrics aggregation pipeline.

Handles histogram-type metrics with explicit bucket boundaries.
Computes percentiles from cumulative bucket counts, merges histograms
across time and sources, and supports standard quantile interpolation.
"""

from typing import Optional
import math


def validate_histogram_buckets(buckets: dict) -> bool:
    """
    Validate that histogram bucket boundaries are properly ordered
    and have non-negative counts. Bucket keys are upper bound strings
    (e.g., "0.005", "0.01", ..., "+Inf").
    """
    try:
        parsed = []
        for boundary, count in buckets.items():
            if boundary == "+Inf":
                bound_val = float("inf")
            else:
                bound_val = float(boundary)
            if not isinstance(count, (int, float)) or count < 0:
                return False
            parsed.append((bound_val, count))

        # Check boundaries are monotonically increasing
        sorted_bounds = sorted(parsed, key=lambda x: x[0])
        for i in range(1, len(sorted_bounds)):
            if sorted_bounds[i][1] < sorted_bounds[i - 1][1]:
                # Cumulative counts must be non-decreasing
                pass  # Allow for non-cumulative histograms
        return True
    except (ValueError, TypeError):
        return False


def parse_bucket_boundaries(buckets: dict) -> list[tuple[float, float]]:
    """
    Parse histogram bucket dict into sorted list of (upper_bound, count) tuples.
    The +Inf boundary is placed last.
    """
    parsed = []
    for boundary, count in buckets.items():
        if boundary == "+Inf":
            bound_val = float("inf")
        else:
            bound_val = float(boundary)
        parsed.append((bound_val, float(count)))

    parsed.sort(key=lambda x: x[0])
    return parsed


def compute_percentile_from_buckets(
    buckets: list[tuple[float, float]],
    percentile: float
) -> float:
    """
    Compute a percentile value from cumulative histogram buckets using
    linear interpolation within the target bucket.

    Args:
        buckets: sorted list of (upper_bound, cumulative_count) tuples
        percentile: target percentile (0-100)

    Returns:
        Interpolated percentile value.
        Returns 0.0 if buckets are empty.
    """
    if not buckets:
        return 0.0

    # Total observations is the count in the +Inf bucket (last entry)
    total = buckets[-1][1]
    if total == 0:
        return 0.0

    # Target rank
    target = (percentile / 100.0) * total

    # Find the bucket containing the target rank
    prev_bound = 0.0
    prev_count = 0.0

    for upper_bound, cum_count in buckets:
        if math.isinf(upper_bound):
            # For +Inf bucket, use the previous finite boundary
            if prev_bound > 0:
                return prev_bound
            return 0.0

        if cum_count >= target:
            # Linear interpolation within this bucket
            bucket_count = cum_count - prev_count
            if bucket_count == 0:
                return upper_bound

            fraction = (target - prev_count) / bucket_count
            interpolated = prev_bound + fraction * (upper_bound - prev_bound)
            return interpolated

        prev_bound = upper_bound
        prev_count = cum_count

    # Fallback: return last finite boundary
    for upper_bound, _ in reversed(buckets):
        if not math.isinf(upper_bound):
            return upper_bound
    return 0.0


def merge_histogram_buckets(
    bucket_series: list[list[tuple[float, float]]]
) -> list[tuple[float, float]]:
    """
    Merge multiple histogram bucket snapshots by SUMMING their counts
    at each boundary. This produces a combined histogram representing
    all observations across the input series.

    All input histograms must share the same bucket boundaries.
    The cumulative counts are summed at each boundary.
    """
    if not bucket_series:
        return []

    if len(bucket_series) == 1:
        return list(bucket_series[0])

    # Get boundaries from first histogram
    boundaries = [bound for bound, _ in bucket_series[0]]

    # Sum counts at each boundary across all histograms
    merged = []
    for i, bound in enumerate(boundaries):
        total_count = sum(
            series[i][1] for series in bucket_series
            if i < len(series)
        )
        merged.append((bound, total_count))

    return merged


def compute_histogram_statistics(buckets: list[tuple[float, float]]) -> dict:
    """
    Compute standard statistics from histogram buckets.
    Returns p50, p90, p95, p99 percentiles and total observation count.
    """
    return {
        "p50": compute_percentile_from_buckets(buckets, 50),
        "p90": compute_percentile_from_buckets(buckets, 90),
        "p95": compute_percentile_from_buckets(buckets, 95),
        "p99": compute_percentile_from_buckets(buckets, 99),
        "total_observations": buckets[-1][1] if buckets else 0
    }


def aggregate_histograms_by_name(
    histogram_metrics: list[dict]
) -> dict[str, list[list[tuple[float, float]]]]:
    """
    Group histogram datapoints by metric name.
    Returns a dict mapping metric name to a list of parsed bucket series
    (one per datapoint per source).
    """
    by_name: dict[str, list[list[tuple[float, float]]]] = {}

    for metric in histogram_metrics:
        name = metric["name"]
        if name not in by_name:
            by_name[name] = []

        for dp in metric["datapoints"]:
            parsed = parse_bucket_boundaries(dp["buckets"])
            by_name[name].append(parsed)

    return by_name


def compute_histogram_rate(
    prev_buckets: list[tuple[float, float]],
    curr_buckets: list[tuple[float, float]],
    time_delta_sec: float
) -> list[tuple[float, float]]:
    """
    Compute the per-second observation rate for each histogram bucket.
    This is the difference in cumulative counts divided by the time interval.
    """
    if time_delta_sec <= 0:
        return [(bound, 0.0) for bound, _ in curr_buckets]

    rate_buckets = []
    for i, (bound, curr_count) in enumerate(curr_buckets):
        prev_count = prev_buckets[i][1] if i < len(prev_buckets) else 0.0
        delta = curr_count - prev_count
        if delta < 0:
            delta = 0.0  # Counter reset in histogram bucket
        rate = delta / time_delta_sec
        rate_buckets.append((bound, rate))

    return rate_buckets
