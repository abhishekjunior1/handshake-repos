"""
Rollup aggregator module for the metrics aggregation pipeline.

Produces downsampled rollup summaries for long-term storage and dashboarding.
Groups metrics into configurable time buckets and computes aggregate statistics
per bucket. Supports multi-level rollups (1m → 5m → 1h) for hierarchical
storage backends like Thanos or Cortex.
"""

from typing import Optional
import math


def compute_time_buckets(
    datapoints: list[dict],
    bucket_duration_sec: float,
    start_timestamp: Optional[float] = None
) -> dict[int, list[dict]]:
    """
    Assign datapoints to fixed-duration time buckets.
    Returns a dict mapping bucket index to list of datapoints in that bucket.
    """
    if not datapoints:
        return {}

    if start_timestamp is None:
        start_timestamp = datapoints[0]["timestamp"]

    buckets: dict[int, list[dict]] = {}
    for dp in datapoints:
        bucket_idx = int((dp["timestamp"] - start_timestamp) // bucket_duration_sec)
        if bucket_idx not in buckets:
            buckets[bucket_idx] = []
        buckets[bucket_idx].append(dp)

    return buckets


def rollup_gauge_bucket(datapoints: list[dict]) -> dict:
    """
    Compute rollup statistics for a bucket of gauge datapoints.
    Produces min, max, mean, count, sum, and last value.
    Skips NaN values (stale markers).
    """
    valid = [dp for dp in datapoints
             if not (isinstance(dp.get("value"), float)
                     and math.isnan(dp["value"]))]

    if not valid:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "count": 0,
            "sum": 0.0,
            "last": None
        }

    values = [dp["value"] for dp in valid]
    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "count": len(values),
        "sum": sum(values),
        "last": values[-1]
    }


def rollup_counter_bucket(rate_records: list[dict]) -> dict:
    """
    Compute rollup statistics for a bucket of counter rate records.
    Produces mean_rate, max_rate, min_rate, and total_delta.
    """
    if not rate_records:
        return {
            "mean_rate": 0.0,
            "max_rate": 0.0,
            "min_rate": 0.0,
            "total_delta": 0.0,
            "sample_count": 0
        }

    rates = [r["rate_per_sec"] for r in rate_records]
    total_delta = sum(r.get("raw_delta", 0.0) for r in rate_records)

    return {
        "mean_rate": sum(rates) / len(rates),
        "max_rate": max(rates),
        "min_rate": min(rates),
        "total_delta": total_delta,
        "sample_count": len(rate_records)
    }


def rollup_histogram_bucket(
    histogram_stats_list: list[dict]
) -> dict:
    """
    Compute rollup for a bucket of histogram percentile snapshots.
    Uses the maximum observed percentile value across snapshots in the bucket
    for p99 (worst-case latency) and mean for p50/p90/p95.
    """
    if not histogram_stats_list:
        return {
            "p50": 0.0,
            "p90": 0.0,
            "p95": 0.0,
            "p99": 0.0,
            "total_observations": 0
        }

    p50_values = [s["p50"] for s in histogram_stats_list]
    p90_values = [s["p90"] for s in histogram_stats_list]
    p95_values = [s["p95"] for s in histogram_stats_list]
    p99_values = [s["p99"] for s in histogram_stats_list]
    total_obs = sum(s.get("total_observations", 0) for s in histogram_stats_list)

    return {
        "p50": sum(p50_values) / len(p50_values),
        "p90": sum(p90_values) / len(p90_values),
        "p95": sum(p95_values) / len(p95_values),
        "p99": max(p99_values),
        "total_observations": total_obs
    }


def generate_rollup_summary(
    counter_rollups: dict[str, list[dict]],
    gauge_rollups: dict[str, list[dict]],
    histogram_rollups: dict[str, list[dict]],
    bucket_duration_sec: float
) -> dict:
    """
    Generate the final rollup summary combining all metric types.
    Returns the complete rollup output structure.
    """
    summary = {
        "rollup_interval_sec": bucket_duration_sec,
        "counters": {},
        "gauges": {},
        "histograms": {}
    }

    for name, buckets in counter_rollups.items():
        summary["counters"][name] = {
            "num_buckets": len(buckets),
            "rollups": buckets
        }

    for name, buckets in gauge_rollups.items():
        summary["gauges"][name] = {
            "num_buckets": len(buckets),
            "rollups": buckets
        }

    for name, buckets in histogram_rollups.items():
        summary["histograms"][name] = {
            "num_buckets": len(buckets),
            "rollups": buckets
        }

    return summary
