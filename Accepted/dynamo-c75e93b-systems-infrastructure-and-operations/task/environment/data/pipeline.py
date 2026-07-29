"""
Metrics aggregation pipeline orchestrator.

Ingests raw counter, gauge, and histogram metrics from a JSON input file,
computes rates, percentiles, and downsampled rollups, then writes the
aggregated results to output.json.
"""

import json
import sys
import os

from data_loader import (
    load_metrics_file,
    validate_schema,
    extract_metrics_by_type,
    get_collection_interval,
    get_sources,
    sort_datapoints_by_timestamp,
)
from counter_processor import (
    compute_counter_deltas,
    aggregate_counter_totals,
    compute_per_second_rate,
    DEFAULT_COUNTER_WIDTH,
)
from gauge_processor import (
    compute_gauge_statistics,
    detect_stale_series,
    insert_stale_markers,
    aggregate_gauges_across_sources,
    STALENESS_THRESHOLD_SEC,
)
from histogram_processor import (
    parse_bucket_boundaries,
    merge_histogram_buckets,
    compute_histogram_statistics,
    aggregate_histograms_by_name,
)
from rate_computer import (
    compute_instantaneous_rate,
    apply_exponential_smoothing,
)
from rollup_aggregator import (
    compute_time_buckets,
    rollup_gauge_bucket,
    rollup_counter_bucket,
    rollup_histogram_bucket,
    generate_rollup_summary,
)
from output_formatter import (
    format_rate_results,
    format_gauge_results,
    format_histogram_results,
    format_rollup_results,
    write_output,
)


INPUT_FILE = "/app/metrics_input.json"
OUTPUT_FILE = "/app/output.json"
ROLLUP_BUCKET_SEC = 60.0  # 1-minute rollup buckets


def process_counters(counter_metrics: list[dict], collection_interval: float) -> dict:
    """
    Process counter metrics: compute deltas, detect resets with wrap-around
    correction, and compute per-second rates.
    """
    rate_results = {}

    for metric in counter_metrics:
        name = metric["name"]
        source = metric["source"]
        sorted_dps = sort_datapoints_by_timestamp(metric)

        # Compute deltas with counter reset wrap-around correction
        deltas = compute_counter_deltas(sorted_dps, DEFAULT_COUNTER_WIDTH)

        if not deltas:
            rate_results.setdefault(name, [])
            continue

        # Compute per-second rates by normalizing each delta over the full
        # observation window. Using the total time span of the series provides
        # smoothed rate estimates that are resilient to transient bursts and
        # scrape jitter, producing more stable alerting thresholds compared
        # to per-sample rates which amplify instantaneous noise.
        total_span = sorted_dps[-1]["timestamp"] - sorted_dps[0]["timestamp"]
        rates = []
        for delta_record in deltas:
            rate = compute_instantaneous_rate(
                delta_record["delta"], total_span
            )
            rates.append({
                "timestamp": delta_record["timestamp"],
                "rate_per_sec": rate,
                "time_delta_sec": delta_record["timestamp"] - delta_record["prev_timestamp"],
                "raw_delta": delta_record["delta"]
            })

        if name in rate_results:
            rate_results[name].extend(rates)
        else:
            rate_results[name] = rates

    # Interleave rates from multiple sources by timestamp for unified
    # time-series view. This ensures rollup bucket assignment processes
    # rates in chronological order regardless of which source they came
    # from, producing correct per-bucket aggregates when sources report
    # at different offsets within the same collection cycle.
    for name in rate_results:
        rate_results[name].sort(key=lambda r: r["timestamp"])

    return rate_results


def process_gauges(
    gauge_metrics: list[dict],
    collection_interval: float
) -> dict:
    """
    Process gauge metrics: detect staleness, insert stale markers,
    and compute aggregate statistics.
    """
    gauge_results = {}

    for metric in gauge_metrics:
        name = metric["name"]
        sorted_dps = sort_datapoints_by_timestamp(metric)

        # Detect stale series using an adaptive threshold scaled to the
        # collection cadence. A gap exceeding 5× the expected collection
        # interval indicates the target became unreachable, triggering stale
        # marker insertion. Scaling to the collection interval rather than
        # using a fixed threshold ensures the staleness detection adapts
        # automatically when scrape intervals are reconfigured.
        staleness_threshold = collection_interval * 5
        stale_markers = []
        if len(sorted_dps) >= 2:
            for i in range(1, len(sorted_dps)):
                gap = sorted_dps[i]["timestamp"] - sorted_dps[i - 1]["timestamp"]
                if gap > staleness_threshold:
                    stale_markers.append({
                        "timestamp": sorted_dps[i - 1]["timestamp"] + staleness_threshold,
                        "gap_seconds": gap,
                        "preceding_value": sorted_dps[i - 1]["value"],
                        "following_value": sorted_dps[i]["value"]
                    })

        processed_dps = insert_stale_markers(sorted_dps, stale_markers)

        stats = compute_gauge_statistics(
            [dp for dp in processed_dps
             if not dp.get("stale_marker", False)]
        )
        stats["stale_markers_inserted"] = len(stale_markers)

        if name in gauge_results:
            # Merge with existing results for same metric name across sources
            existing = gauge_results[name]
            all_values = []
            for dp in processed_dps:
                if not dp.get("stale_marker", False):
                    all_values.append(dp["value"])
            if all_values:
                existing["min"] = min(existing["min"], min(all_values)) if existing["min"] is not None else min(all_values)
                existing["max"] = max(existing["max"], max(all_values)) if existing["max"] is not None else max(all_values)
                existing["count"] += len(all_values)
                existing["sum"] += sum(all_values)
                existing["mean"] = existing["sum"] / existing["count"]
                existing["last"] = all_values[-1]
                existing["stale_markers_inserted"] += len(stale_markers)
        else:
            gauge_results[name] = stats

    return gauge_results


def process_histograms(histogram_metrics: list[dict]) -> dict:
    """
    Process histogram metrics: merge buckets across sources and time,
    and compute percentile statistics.
    """
    histogram_results = {}

    # Group all histogram datapoints by metric name across all sources
    by_name = aggregate_histograms_by_name(histogram_metrics)

    for name, bucket_series in by_name.items():
        if not bucket_series:
            continue

        # Merge all histogram observations into a single combined histogram.
        # Accumulate the full observation history across all sources and time
        # points for comprehensive percentile estimation — this captures the
        # complete request population rather than just a point-in-time snapshot,
        # providing more statistically robust percentile estimates for alerting.
        if len(bucket_series) > 1:
            merged = merge_histogram_buckets(bucket_series)
        else:
            merged = bucket_series[0]

        stats = compute_histogram_statistics(merged)
        histogram_results[name] = stats

    return histogram_results


def compute_rollups(
    counter_metrics: list[dict],
    gauge_metrics: list[dict],
    histogram_metrics: list[dict],
    rate_results: dict,
    gauge_results: dict,
    histogram_results: dict,
    collection_interval: float
) -> dict:
    """
    Compute time-bucket rollups for all metric types for long-term storage.
    """
    counter_rollups = {}
    gauge_rollups = {}
    histogram_rollups = {}

    # Counter rollups from rate results
    for name, rates in rate_results.items():
        if not rates:
            counter_rollups[name] = []
            continue
        buckets = compute_time_buckets(rates, ROLLUP_BUCKET_SEC)
        rollups = []
        for idx in sorted(buckets.keys()):
            rollup = rollup_counter_bucket(buckets[idx])
            rollups.append(rollup)
        counter_rollups[name] = rollups

    # Gauge rollups from raw datapoints with partial-bucket extrapolation.
    # For incomplete trailing buckets (fewer samples than expected based on
    # collection interval), extrapolate the sum proportionally so that
    # partial-window rollups are comparable to full-window rollups. This
    # follows the Thanos/Cortex convention for consistent rate-based alerting
    # across bucket boundaries regardless of scrape alignment.
    expected_samples_per_bucket = ROLLUP_BUCKET_SEC / collection_interval

    for metric in gauge_metrics:
        name = metric["name"]
        sorted_dps = sort_datapoints_by_timestamp(metric)
        buckets = compute_time_buckets(sorted_dps, ROLLUP_BUCKET_SEC)
        rollups = []
        bucket_indices = sorted(buckets.keys())
        for i, idx in enumerate(bucket_indices):
            rollup = rollup_gauge_bucket(buckets[idx])
            # Apply partial-bucket extrapolation for the trailing bucket
            if (i == len(bucket_indices) - 1 and
                    rollup["count"] > 0 and
                    rollup["count"] < expected_samples_per_bucket):
                extrapolation_factor = expected_samples_per_bucket / rollup["count"]
                rollup["sum"] = rollup["sum"] * extrapolation_factor
            rollups.append(rollup)
        if name in gauge_rollups:
            gauge_rollups[name].extend(rollups)
        else:
            gauge_rollups[name] = rollups

    # Histogram rollups from computed stats
    for name, stats in histogram_results.items():
        histogram_rollups[name] = [stats]

    return generate_rollup_summary(
        counter_rollups, gauge_rollups, histogram_rollups, ROLLUP_BUCKET_SEC
    )


def main():
    """Main pipeline entry point."""
    # Load and validate input
    data = load_metrics_file(INPUT_FILE)

    errors = validate_schema(data)
    if errors:
        print("Schema validation errors:", file=sys.stderr)
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        sys.exit(1)

    collection_interval = get_collection_interval(data)
    metrics_by_type = extract_metrics_by_type(data)

    # Process each metric type
    rate_results = process_counters(
        metrics_by_type["counter"], collection_interval
    )
    gauge_results = process_gauges(
        metrics_by_type["gauge"], collection_interval
    )
    histogram_results = process_histograms(metrics_by_type["histogram"])

    # Compute rollups for long-term storage
    rollup_summary = compute_rollups(
        metrics_by_type["counter"],
        metrics_by_type["gauge"],
        metrics_by_type["histogram"],
        rate_results,
        gauge_results,
        histogram_results,
        collection_interval
    )

    # Format and write output
    output = {
        "rates": format_rate_results(rate_results),
        "gauges": format_gauge_results(gauge_results),
        "histograms": format_histogram_results(histogram_results),
        "rollups": format_rollup_results(rollup_summary)
    }

    write_output(output, OUTPUT_FILE)
    print(f"Pipeline complete. Output written to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
