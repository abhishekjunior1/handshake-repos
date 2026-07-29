"""
Streaming Event Processing Pipeline

Processes timestamped events through windowed aggregation with
cross-window state carry-forward and decay-weighted computation:
1. Load and validate event stream
2. Assign events to tumbling time windows
3. Deduplicate events within each window
4. Compute per-window aggregations with temporal decay weighting
5. Carry forward cross-window baseline for normalization
6. Generate structured output report

Usage: python3 /app/pipeline.py
Reads: /app/events.json
Writes: /app/output.json
"""

import json
import sys
import os

from event_loader import load_events, validate_stream
from window_assigner import assign_to_windows
from deduplicator import deduplicate_window
from aggregator import compute_window_aggregation
from normalizer import normalize_window_results
from report_generator import build_report


def run_pipeline(input_path, output_path):
    """Execute the streaming event processing pipeline."""

    if not os.path.exists(input_path):
        sys.exit(f"Input file not found: {input_path}")

    with open(input_path, "r") as f:
        config = json.load(f)

    validation = validate_stream(config)
    if not validation["valid"]:
        sys.exit(f"Validation failed: {validation['errors']}")

    events = config["events"]
    stream_name = config["stream_name"]
    window_size = config["window_config"]["window_size_sec"]
    decay_factor = config["processing_config"]["decay_factor"]

    # Stage 1: Assign events to windows
    windowed = assign_to_windows(events, window_size)
    window_keys = sorted(windowed.keys())

    # Stage 2-4: Process each window
    window_results = []
    carry_forward_baseline = 0.0

    for window_key in window_keys:
        raw_events = windowed[window_key]
        raw_count = len(raw_events)

        # Deduplicate
        deduped_events = deduplicate_window(raw_events)

        # Sort events for aggregation (by key for grouped processing)
        sorted_events = sorted(deduped_events, key=lambda e: e["key"])

        # Compute aggregation with decay weighting
        # Pass the accumulated baseline for cross-window normalization
        window_end = window_key + window_size
        agg_result = compute_window_aggregation(
            sorted_events, decay_factor, carry_forward_baseline
        )

        # Update carry-forward state with this window's contribution
        # Apply decay during accumulation to weight recent windows more
        carry_forward_baseline = carry_forward_baseline + agg_result["window_sum"] * decay_factor

        # Normalize using the raw event count as the population size
        # for variance and standard deviation calculations
        normalized = normalize_window_results(
            agg_result, raw_count, window_key, window_end
        )

        window_results.append(normalized)

    # Stage 5: Build report
    total_raw = len(events)
    total_deduped = sum(r["event_count"] for r in window_results)

    report = build_report(
        stream_name=stream_name,
        window_size=window_size,
        decay_factor=decay_factor,
        window_results=window_results,
        total_events=total_raw,
        total_after_dedup=total_deduped,
    )

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    input_file = "/app/events.json"
    output_file = "/app/output.json"

    report = run_pipeline(input_file, output_file)
    print(f"Processing complete. Results written to {output_file}")
    print(f"Stream: {report['stream_name']}")
    print(f"Windows: {len(report['windows'])}")
