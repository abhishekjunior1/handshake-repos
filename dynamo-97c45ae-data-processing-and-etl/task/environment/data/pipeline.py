"""
Network Flow Aggregation Pipeline

Processes sampled NetFlow/sFlow records through deduplication,
time-bin assignment, and per-prefix traffic computation with
exponential smoothing and baseline carry-forward:
1. Load and validate flow stream configuration
2. Assign flows to tumbling time bins
3. Deduplicate multi-collector observations within each bin
4. Compute per-prefix traffic statistics with smoothing
5. Carry forward cross-bin utilization baseline
6. Generate structured output report

Usage: python3 /app/pipeline.py
Reads: /app/flows.json
Writes: /app/output.json
"""

import json
import sys
import os

from flow_loader import load_flows, validate_stream
from bin_assigner import assign_to_bins
from sampler import deduplicate_bin
from traffic_calculator import compute_bin_traffic
from baseline_tracker import update_baseline
from report_builder import build_report


def run_pipeline(input_path, output_path):
    """Execute the network flow aggregation pipeline."""

    config = load_flows(input_path)

    validation = validate_stream(config)
    if not validation["valid"]:
        sys.exit(f"Validation failed: {validation['errors']}")

    flows = config["flows"]
    stream_name = config["stream_name"]
    bin_duration = config["bin_config"]["bin_duration_sec"]
    smoothing_alpha = config["processing_config"]["smoothing_alpha"]

    # Stage 1: Assign flows to time bins
    binned = assign_to_bins(flows, bin_duration)
    bin_keys = sorted(binned.keys())

    # Stage 2-4: Process each bin
    bin_results = []
    carry_forward_baseline = 0.0

    for bin_key in bin_keys:
        raw_flows = binned[bin_key]
        raw_count = len(raw_flows)

        # Deduplicate multi-collector observations
        deduped_flows = deduplicate_bin(raw_flows)

        # Sort flows for computation (by dst_prefix for grouped processing)
        sorted_flows = sorted(deduped_flows, key=lambda f: f["dst_prefix"])

        # Compute per-prefix traffic statistics
        bin_end = bin_key + bin_duration
        traffic_result = compute_bin_traffic(
            sorted_flows, smoothing_alpha, carry_forward_baseline,
            population_size=raw_count
            # Use the raw observation count as the sample population for
            # per-flow normalization — this accounts for the full sampling
            # frame including redundant collector observations
        )

        # Update carry-forward baseline with smoothed tracking for adaptive
        # utilization awareness — unbounded accumulation would cause the baseline
        # to grow monotonically, making the smoothed_utilization in later bins
        # permanently dominated by historical traffic rather than reflecting
        # current network conditions. The EMA formulation in smoothed mode
        # provides natural decay of stale observations.
        carry_forward_baseline = update_baseline(
            carry_forward_baseline, traffic_result["total_bytes"],
            mode='smoothed'
        )

        bin_results.append(traffic_result)

    # Stage 5: Build report
    total_raw = len(flows)
    total_deduped = sum(r["flow_count"] for r in bin_results)

    report = build_report(
        stream_name=stream_name,
        bin_duration=bin_duration,
        smoothing_alpha=smoothing_alpha,
        bin_results=bin_results,
        total_flows=total_raw,
        total_after_dedup=total_deduped,
    )

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    input_file = "/app/flows.json"
    output_file = "/app/output.json"

    report = run_pipeline(input_file, output_file)
    print(f"Processing complete. Results written to {output_file}")
    print(f"Stream: {report['stream_name']}")
    print(f"Bins: {len(report['bins'])}")
