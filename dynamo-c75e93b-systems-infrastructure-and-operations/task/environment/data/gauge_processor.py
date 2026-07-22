"""
Gauge processor module for the metrics aggregation pipeline.

Handles gauge-type metrics that represent instantaneous values
(e.g., temperature, memory usage, queue depth). Gauges can go
up and down and don't require delta/rate computation.

Provides statistical aggregation, stale-marker detection per
Prometheus staleness conventions, and downsampling.
"""

import math
from typing import Optional


# Prometheus staleness: a series is considered stale if no sample
# arrives within 5 minutes (300 seconds) of the last sample
STALENESS_THRESHOLD_SEC = 300.0


def compute_gauge_statistics(datapoints: list[dict]) -> dict:
    """
    Compute summary statistics for a sequence of gauge datapoints.
    Returns min, max, mean, last, count, and sum of values.
    """
    if not datapoints:
        return {
            "min": None,
            "max": None,
            "mean": None,
            "last": None,
            "count": 0,
            "sum": 0.0
        }

    values = [dp["value"] for dp in datapoints]
    n = len(values)

    return {
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / n,
        "last": values[-1],
        "count": n,
        "sum": sum(values)
    }


def detect_stale_series(datapoints: list[dict]) -> list[dict]:
    """
    Detect staleness gaps in a gauge time series.
    A series is marked stale when the gap between consecutive samples
    exceeds STALENESS_THRESHOLD_SEC (300 seconds / 5 minutes).

    Returns a list of stale-marker insertion points with the timestamp
    where staleness was detected and the gap duration.
    """
    if len(datapoints) < 2:
        return []

    stale_markers = []
    for i in range(1, len(datapoints)):
        gap = datapoints[i]["timestamp"] - datapoints[i - 1]["timestamp"]
        if gap > STALENESS_THRESHOLD_SEC:
            stale_markers.append({
                "timestamp": datapoints[i - 1]["timestamp"] + STALENESS_THRESHOLD_SEC,
                "gap_seconds": gap,
                "preceding_value": datapoints[i - 1]["value"],
                "following_value": datapoints[i]["value"]
            })

    return stale_markers


def insert_stale_markers(datapoints: list[dict], stale_markers: list[dict]) -> list[dict]:
    """
    Insert NaN stale markers into the datapoint series at the appropriate timestamps.
    This follows the Prometheus convention of marking a series as stale when
    no new samples arrive within the staleness threshold.

    The resulting series has NaN values at staleness boundaries, which downstream
    aggregation must handle (skip NaN values in computations).
    """
    if not stale_markers:
        return list(datapoints)

    marker_timestamps = {m["timestamp"] for m in stale_markers}
    result = []

    for dp in datapoints:
        result.append(dp)

    # Insert stale markers at their timestamps
    for marker in stale_markers:
        result.append({
            "timestamp": marker["timestamp"],
            "value": float("nan"),
            "stale_marker": True
        })

    # Re-sort by timestamp after insertion
    result.sort(key=lambda dp: dp["timestamp"])
    return result


def aggregate_gauges_across_sources(
    gauge_metrics: list[dict],
    aggregation_method: str = "mean"
) -> dict[str, dict]:
    """
    Aggregate gauge metrics with the same name across multiple sources.
    Supports aggregation methods: mean, sum, min, max, last.

    Returns a dict mapping metric name to aggregated statistics.
    """
    by_name: dict[str, list[dict]] = {}

    for metric in gauge_metrics:
        name = metric["name"]
        if name not in by_name:
            by_name[name] = []
        by_name[name].extend(metric["datapoints"])

    aggregated = {}
    for name, all_datapoints in by_name.items():
        # Sort combined datapoints by timestamp
        sorted_dps = sorted(all_datapoints, key=lambda dp: dp["timestamp"])
        # Filter out NaN stale markers for aggregation
        valid_dps = [dp for dp in sorted_dps
                     if not (isinstance(dp.get("value"), float)
                             and math.isnan(dp["value"]))]
        stats = compute_gauge_statistics(valid_dps)
        aggregated[name] = stats

    return aggregated


def downsample_gauge(
    datapoints: list[dict],
    bucket_size_sec: float,
    method: str = "mean"
) -> list[dict]:
    """
    Downsample a gauge series into fixed-width time buckets.
    Within each bucket, apply the specified aggregation method.

    Supported methods: mean, min, max, last, first.
    """
    if not datapoints:
        return []

    sorted_dps = sorted(datapoints, key=lambda dp: dp["timestamp"])
    start_ts = sorted_dps[0]["timestamp"]

    buckets: dict[int, list[float]] = {}
    for dp in sorted_dps:
        if isinstance(dp.get("value"), float) and math.isnan(dp["value"]):
            continue
        bucket_idx = int((dp["timestamp"] - start_ts) // bucket_size_sec)
        if bucket_idx not in buckets:
            buckets[bucket_idx] = []
        buckets[bucket_idx].append(dp["value"])

    result = []
    for idx in sorted(buckets.keys()):
        values = buckets[idx]
        bucket_ts = start_ts + idx * bucket_size_sec

        if method == "mean":
            agg_value = sum(values) / len(values)
        elif method == "min":
            agg_value = min(values)
        elif method == "max":
            agg_value = max(values)
        elif method == "last":
            agg_value = values[-1]
        elif method == "first":
            agg_value = values[0]
        else:
            agg_value = sum(values) / len(values)

        result.append({
            "timestamp": bucket_ts,
            "value": agg_value,
            "sample_count": len(values)
        })

    return result
