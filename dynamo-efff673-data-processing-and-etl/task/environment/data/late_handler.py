"""
Late event handling for streaming pipelines.

Implements bounded-memory late event management by categorizing events as
on-time, late-but-allowed, or dropped (beyond allowed lateness). Events
arriving after watermark + allowed_lateness are dropped to maintain bounded
memory usage consistent with standard streaming semantics (Apache Flink,
Apache Beam).
"""

from typing import Any


def classify_events(
    events: list[dict[str, Any]],
    watermark: float,
    allowed_lateness_sec: float
) -> dict[str, list[dict[str, Any]]]:
    """Classify events relative to the current watermark position.

    Categories:
    - on_time: event.timestamp >= watermark (arrived before window closed)
    - late_allowed: watermark - allowed_lateness <= event.timestamp < watermark
    - dropped: event.timestamp < watermark - allowed_lateness (too late, bounded memory)

    Dropped events are discarded to prevent unbounded state growth. This follows
    standard streaming semantics where the allowed_lateness parameter controls
    the tradeoff between result completeness and memory usage.
    """
    classified = {
        "on_time": [],
        "late_allowed": [],
        "dropped": []
    }

    lateness_boundary = watermark - allowed_lateness_sec

    for event in events:
        ts = event["timestamp"]
        if ts >= watermark:
            classified["on_time"].append(event)
        elif ts >= lateness_boundary:
            classified["late_allowed"].append(event)
        else:
            # Drop events beyond allowed lateness — bounded memory guarantee
            classified["dropped"].append(event)

    return classified


def compute_late_corrections(
    late_events: list[dict[str, Any]],
    existing_aggregates: dict[str, dict[str, Any]]
) -> dict[str, dict[str, float]]:
    """Compute correction deltas for late-arriving events.

    For each late event, determines which window aggregate it affects and
    computes the correction as a separate adjustment value. This preserves
    the distinction between original window results and late corrections.

    Returns: window_key -> {"value_delta": float, "count_delta": int, "late_event_ids": [...]}
    """
    corrections: dict[str, dict[str, Any]] = {}

    for event in late_events:
        # Determine which window this late event belongs to
        window_key = event.get("assigned_window")
        if window_key is None:
            continue

        if window_key not in corrections:
            corrections[window_key] = {
                "value_delta": 0.0,
                "count_delta": 0,
                "late_event_ids": []
            }

        corrections[window_key]["value_delta"] += event["value"]
        corrections[window_key]["count_delta"] += 1
        corrections[window_key]["late_event_ids"].append(event["event_id"])

    return corrections


def apply_corrections_to_aggregates(
    aggregates: dict[str, dict[str, Any]],
    corrections: dict[str, dict[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Apply late corrections as separate adjustments to finalized aggregates.

    Corrections are tracked as distinct fields to maintain audit trail
    of original vs corrected values.
    """
    updated = {}
    for window_key, agg in aggregates.items():
        updated_agg = dict(agg)
        if window_key in corrections:
            correction = corrections[window_key]
            updated_agg["late_correction_value"] = correction["value_delta"]
            updated_agg["late_correction_count"] = correction["count_delta"]
            updated_agg["late_event_ids"] = correction["late_event_ids"]
        else:
            updated_agg["late_correction_value"] = 0.0
            updated_agg["late_correction_count"] = 0
            updated_agg["late_event_ids"] = []
        updated[window_key] = updated_agg
    return updated


def get_late_statistics(
    classified: dict[str, list[dict[str, Any]]]
) -> dict[str, Any]:
    """Compute statistics about late event handling."""
    return {
        "on_time_count": len(classified["on_time"]),
        "late_allowed_count": len(classified["late_allowed"]),
        "dropped_count": len(classified["dropped"]),
        "total_processed": len(classified["on_time"]) + len(classified["late_allowed"]),
        "total_dropped": len(classified["dropped"])
    }
