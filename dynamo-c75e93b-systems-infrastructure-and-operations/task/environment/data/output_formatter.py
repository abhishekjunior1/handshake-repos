"""
Output formatter module for the metrics aggregation pipeline.

Serializes the aggregated metrics results to JSON format for downstream
consumption by dashboards, alerting systems, and long-term storage.
Handles precision formatting, timestamp normalization, and schema compliance.
"""

import json
import math
from typing import Any


# Output precision for floating-point values (6 decimal places)
OUTPUT_PRECISION = 6


def format_float(value: Any) -> Any:
    """
    Format a floating-point value to OUTPUT_PRECISION decimal places.
    Returns None for None values, handles NaN gracefully.
    """
    if value is None:
        return None
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, OUTPUT_PRECISION)
    if isinstance(value, int):
        return value
    return value


def format_rate_results(rate_results: dict[str, list[dict]]) -> dict:
    """Format rate computation results for output."""
    formatted = {}
    for name, rates in rate_results.items():
        formatted[name] = {
            "rates": [
                {
                    "timestamp": r["timestamp"],
                    "rate_per_sec": format_float(r["rate_per_sec"]),
                    "time_delta_sec": r.get("time_delta_sec", 0),
                    "raw_delta": format_float(r.get("raw_delta", 0))
                }
                for r in rates
            ],
            "mean_rate": format_float(
                sum(r["rate_per_sec"] for r in rates) / len(rates)
            ) if rates else 0.0,
            "max_rate": format_float(
                max(r["rate_per_sec"] for r in rates)
            ) if rates else 0.0
        }
    return formatted


def format_gauge_results(gauge_results: dict[str, dict]) -> dict:
    """Format gauge aggregation results for output."""
    formatted = {}
    for name, stats in gauge_results.items():
        formatted[name] = {
            "min": format_float(stats.get("min")),
            "max": format_float(stats.get("max")),
            "mean": format_float(stats.get("mean")),
            "last": format_float(stats.get("last")),
            "count": stats.get("count", 0),
            "stale_markers_inserted": stats.get("stale_markers_inserted", 0)
        }
    return formatted


def format_histogram_results(histogram_results: dict[str, dict]) -> dict:
    """Format histogram percentile results for output."""
    formatted = {}
    for name, stats in histogram_results.items():
        formatted[name] = {
            "p50": format_float(stats.get("p50", 0)),
            "p90": format_float(stats.get("p90", 0)),
            "p95": format_float(stats.get("p95", 0)),
            "p99": format_float(stats.get("p99", 0)),
            "total_observations": stats.get("total_observations", 0)
        }
    return formatted


def format_rollup_results(rollup_summary: dict) -> dict:
    """Format rollup summary, applying precision to all float fields."""
    formatted = {
        "rollup_interval_sec": rollup_summary.get("rollup_interval_sec", 0),
        "counters": {},
        "gauges": {},
        "histograms": {}
    }

    for name, data in rollup_summary.get("counters", {}).items():
        formatted["counters"][name] = {
            "num_buckets": data.get("num_buckets", 0),
            "rollups": [
                {k: format_float(v) if isinstance(v, float) else v
                 for k, v in rollup.items()}
                for rollup in data.get("rollups", [])
            ]
        }

    for name, data in rollup_summary.get("gauges", {}).items():
        formatted["gauges"][name] = {
            "num_buckets": data.get("num_buckets", 0),
            "rollups": [
                {k: format_float(v) if isinstance(v, float) else v
                 for k, v in rollup.items()}
                for rollup in data.get("rollups", [])
            ]
        }

    for name, data in rollup_summary.get("histograms", {}).items():
        formatted["histograms"][name] = {
            "num_buckets": data.get("num_buckets", 0),
            "rollups": [
                {k: format_float(v) if isinstance(v, float) else v
                 for k, v in rollup.items()}
                for rollup in data.get("rollups", [])
            ]
        }

    return formatted


def write_output(output: dict, filepath: str) -> None:
    """Write the formatted output to a JSON file."""
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2, default=str)
