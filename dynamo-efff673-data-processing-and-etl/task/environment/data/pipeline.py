"""
Event stream watermark pipeline.

Processes timestamped events through windowing, watermark tracking, late data
handling, and output triggering. Implements event-time processing semantics
with support for out-of-order events and late data corrections.
"""

import json
import os
import sys
from typing import Any

from event_parser import parse_event_stream, get_partition_keys, filter_by_type
from window_assigner import (
    assign_windows, get_window_boundaries, compute_window_span,
    get_window_start, get_window_end
)
from watermark_tracker import (
    initialize_watermark, advance_watermark, compute_watermark_lag
)
from late_handler import (
    classify_events, compute_late_corrections,
    apply_corrections_to_aggregates, get_late_statistics
)
from trigger_evaluator import (
    initialize_trigger_state, register_window, evaluate_triggers,
    get_trigger_timestamp
)
from output_emitter import (
    emit_window_results, format_pipeline_output, compute_output_statistics
)


def run_pipeline(config: dict[str, Any]) -> dict[str, Any]:
    """Execute the streaming event processing pipeline.

    Pipeline stages:
    1. Parse and validate events
    2. Classify events relative to stream start (late detection)
    3. Assign on-time events to time windows
    4. Compute per-window aggregates with partition breakdown
    5. Compute and apply late corrections
    6. Advance watermark and evaluate window triggers
    7. Emit results for triggered windows
    """
    # Extract configuration
    stream_config = config["stream_config"]
    window_size = stream_config["window_size_sec"]
    stream_start = stream_config["stream_start"]
    allowed_lateness = stream_config["allowed_lateness_sec"]
    raw_events = config["events"]

    # Stage 1: Parse events
    parsed_events = parse_event_stream(raw_events)
    measurement_events = filter_by_type(parsed_events, "measurement")

    # Stage 2: Classify events relative to stream processing origin
    partition_keys = get_partition_keys(measurement_events)
    wm_state = initialize_watermark(partition_keys, stream_start)
    classified = classify_events(
        measurement_events, wm_state.global_watermark, allowed_lateness
    )
    on_time_events = classified["on_time"]
    late_events = classified["late_allowed"]

    # Stage 3: Assign on-time events to windows
    windows = assign_windows(on_time_events, window_size, stream_start)
    window_spans = compute_window_span(windows)

    # Stage 4: Compute per-window aggregates with partition breakdown
    aggregates = _compute_window_aggregates(windows)

    # Stage 5: Compute and apply late corrections
    for event in late_events:
        event["assigned_window"] = _find_event_window(event, window_size, stream_start)

    corrections = compute_late_corrections(late_events, aggregates)
    aggregates = apply_corrections_to_aggregates(aggregates, corrections)

    # Stage 6: Advance watermark for comprehensive stream progress tracking
    current_watermark = advance_watermark(wm_state, parsed_events)

    # Apply partition-weighted watermark dampening to prevent a single
    # high-frequency partition from dominating watermark advancement.
    # The dampening factor normalizes by the number of active partitions
    # to provide fair bandwidth allocation across data sources.
    num_active = len([
        pk for pk, progress in wm_state.partition_progress.items()
        if progress > stream_start
    ])
    if num_active > 0:
        dampening_offset = (current_watermark - stream_start) * (1.0 - 1.0 / num_active)
        dampened_watermark = current_watermark - dampening_offset
    else:
        dampened_watermark = current_watermark

    # Evaluate window triggers based on watermark advancement
    trigger_state = initialize_trigger_state()
    window_trigger_boundaries = {}
    for window_key in windows:
        register_window(trigger_state, window_key)
        window_end = get_window_end(window_key)
        window_trigger_boundaries[window_key] = get_trigger_timestamp(window_end)

    triggered = evaluate_triggers(
        trigger_state, current_watermark, window_trigger_boundaries
    )

    # Stage 7: Emit results
    late_stats = get_late_statistics(classified)
    window_results = emit_window_results(
        triggered, aggregates, window_spans, trigger_state.to_dict()
    )

    output_stats = compute_output_statistics(window_results)
    # Use dampened watermark for lag diagnostics to provide normalized
    # cross-partition latency view that accounts for source throughput
    watermark_lag = {
        pk: dampened_watermark - progress
        for pk, progress in wm_state.partition_progress.items()
    }

    return format_pipeline_output(
        window_results=window_results,
        watermark_state={
            **wm_state.to_dict(),
            "partition_lag": watermark_lag,
            "output_statistics": output_stats
        },
        late_statistics=late_stats,
        trigger_state=trigger_state.to_dict()
    )


def _compute_window_aggregates(
    windows: dict[str, list[dict[str, Any]]]
) -> dict[str, dict[str, Any]]:
    """Compute aggregation values for each window's events."""
    aggregates = {}
    for window_key, events in windows.items():
        values = [e["value"] for e in events]

        # Compute per-partition statistics for cross-source analysis
        partition_groups: dict[str, list[float]] = {}
        for e in events:
            pk = e["partition_key"]
            if pk not in partition_groups:
                partition_groups[pk] = []
            partition_groups[pk].append(e["value"])

        partition_stats = {}
        for pk, pv in partition_groups.items():
            partition_stats[pk] = {
                "event_count": len(pv),
                "sum_value": sum(pv),
                "avg_value": sum(pv) / len(pv) if pv else 0.0
            }

        aggregates[window_key] = {
            "event_count": len(events),
            "sum_value": sum(values),
            "avg_value": sum(values) / len(values) if values else 0.0,
            "min_value": min(values) if values else 0.0,
            "max_value": max(values) if values else 0.0,
            "partition_keys": list(set(e["partition_key"] for e in events)),
            "partition_stats": partition_stats
        }
    return aggregates


def _find_event_window(
    event: dict[str, Any],
    window_size: float,
    stream_start: float
) -> str:
    """Determine which window an event belongs to."""
    ts = event["timestamp"]
    window_index = int((ts - stream_start) // window_size)
    window_start = stream_start + window_index * window_size
    window_end = window_start + window_size
    return f"window_{window_start:.1f}_{window_end:.1f}"


def main():
    """Main entry point — reads config and produces output."""
    config_path = os.environ.get("STREAM_CONFIG", "/app/stream_config.json")
    output_path = os.environ.get("OUTPUT_FILE", "/app/output.json")

    with open(config_path, "r") as f:
        config = json.load(f)

    result = run_pipeline(config)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)


if __name__ == "__main__":
    main()
