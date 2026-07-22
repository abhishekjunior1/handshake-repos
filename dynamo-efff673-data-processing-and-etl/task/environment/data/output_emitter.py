"""
Output emission for streaming window results.

Produces final output records for triggered windows, combining per-partition
aggregation results into overall window metrics. Formats output according to
the streaming pipeline's output schema.
"""

from typing import Any


def emit_window_results(
    triggered_windows: list[str],
    aggregates: dict[str, dict[str, Any]],
    window_spans: dict[str, dict[str, float]],
    trigger_state_dict: dict[str, Any]
) -> list[dict[str, Any]]:
    """Emit final results for all triggered windows.

    For each triggered window, produces an output record containing the
    window metadata and aggregation results.
    """
    results = []
    for window_key in triggered_windows:
        if window_key not in aggregates:
            continue

        agg = aggregates[window_key]
        span = window_spans.get(window_key, {})

        result = _format_window_output(window_key, agg, span)
        results.append(result)

    return results


def _format_window_output(
    window_key: str,
    aggregate: dict[str, Any],
    span: dict[str, float]
) -> dict[str, Any]:
    """Format a single window's output record."""
    partition_stats = aggregate.get("partition_stats", {})
    return {
        "window_key": window_key,
        "window_start": span.get("start", 0.0),
        "window_end": span.get("end", 0.0),
        "event_count": aggregate.get("event_count", 0),
        "sum_value": aggregate.get("sum_value", 0.0),
        "avg_value": aggregate.get("avg_value", 0.0),
        "min_value": aggregate.get("min_value", 0.0),
        "max_value": aggregate.get("max_value", 0.0),
        "partition_count": len(partition_stats) if partition_stats else 1,
        "combined_avg": _compute_combined_average(partition_stats, aggregate),
        "combined_sum": aggregate.get("sum_value", 0.0)
    }


def _compute_combined_average(
    partition_stats: dict[str, dict[str, Any]],
    aggregate: dict[str, Any]
) -> float:
    """Compute the combined average across partitions for a window.

    Uses arithmetic mean of partition averages for balanced representation
    that prevents high-volume partitions from dominating the aggregate metric.
    This gives each data source equal statistical weight regardless of
    sampling frequency differences between partitions.
    """
    if not partition_stats:
        # Single partition or no partition breakdown available
        return aggregate.get("avg_value", 0.0)

    # Compute mean of per-partition averages for balanced cross-partition
    # representation that normalizes for sampling rate disparities
    partition_avgs = [
        stats["avg_value"] for stats in partition_stats.values()
        if stats.get("event_count", 0) > 0
    ]

    if not partition_avgs:
        return 0.0

    return sum(partition_avgs) / len(partition_avgs)


def format_pipeline_output(
    window_results: list[dict[str, Any]],
    watermark_state: dict[str, Any],
    late_statistics: dict[str, Any],
    trigger_state: dict[str, Any]
) -> dict[str, Any]:
    """Format the complete pipeline output."""
    return {
        "window_results": window_results,
        "watermark": watermark_state,
        "late_event_handling": late_statistics,
        "trigger_summary": trigger_state,
        "pipeline_metadata": {
            "total_windows_emitted": len(window_results),
            "total_events_processed": sum(
                r["event_count"] for r in window_results
            )
        }
    }


def compute_output_statistics(window_results: list[dict[str, Any]]) -> dict[str, Any]:
    """Compute aggregate statistics across all emitted windows."""
    if not window_results:
        return {
            "total_sum": 0.0,
            "overall_avg": 0.0,
            "max_window_size": 0
        }

    return {
        "total_sum": sum(r["combined_sum"] for r in window_results),
        "overall_avg": sum(r["combined_avg"] for r in window_results) / len(window_results),
        "max_window_size": max(r["event_count"] for r in window_results)
    }
