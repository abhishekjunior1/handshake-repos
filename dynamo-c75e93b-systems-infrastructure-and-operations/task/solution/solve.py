"""
Solution for the metrics aggregation pipeline.
Patches the three bugs in pipeline.py and re-runs the pipeline.
"""

import subprocess
import sys


def patch_pipeline():
    """Apply fixes to pipeline.py"""
    with open("/app/pipeline.py", "r") as f:
        content = f.read()

    # Fix 1: Rate computation should divide each delta by its own time interval,
    # not by the total span of the entire series. Per-second rate = delta / dt.
    content = content.replace(
        """        # Compute per-second rates by normalizing each delta over the full
        # observation window. Using the total time span of the series provides
        # smoothed rate estimates that are resilient to transient bursts and
        # scrape jitter, producing more stable alerting thresholds compared
        # to per-sample rates which amplify instantaneous noise.
        total_span = sorted_dps[-1]["timestamp"] - sorted_dps[0]["timestamp"]
        rates = []
        for delta_record in deltas:
            rate = compute_instantaneous_rate(
                delta_record["delta"], total_span
            )""",
        """        rates = []
        for delta_record in deltas:
            time_delta = delta_record["timestamp"] - delta_record["prev_timestamp"]
            rate = compute_instantaneous_rate(
                delta_record["delta"], time_delta
            )"""
    )

    # Fix 2: Histogram percentiles should merge only the LATEST cumulative
    # snapshot per source, not all historical snapshots (which double-counts).
    content = content.replace(
        """    # Group all histogram datapoints by metric name across all sources
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
        histogram_results[name] = stats""",
        """    # Group histograms by name, taking only the latest datapoint per source
    by_name_latest = {}
    for metric in histogram_metrics:
        name = metric["name"]
        source = metric["source"]
        sorted_dps = sort_datapoints_by_timestamp(metric)
        if name not in by_name_latest:
            by_name_latest[name] = {}
        latest_dp = sorted_dps[-1]
        by_name_latest[name][source] = parse_bucket_boundaries(latest_dp["buckets"])

    for name, sources in by_name_latest.items():
        bucket_series = list(sources.values())
        if len(bucket_series) > 1:
            merged = merge_histogram_buckets(bucket_series)
        else:
            merged = bucket_series[0]

        stats = compute_histogram_statistics(merged)
        histogram_results[name] = stats"""
    )

    # Fix 3: Stale-marker detection should use the standard STALENESS_THRESHOLD_SEC
    # (300 seconds) from gauge_processor, not collection_interval * 5.
    content = content.replace(
        """        # Detect stale series using an adaptive threshold scaled to the
        # collection cadence. A gap exceeding 5\u00d7 the expected collection
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
                    })""",
        """        stale_markers = detect_stale_series(sorted_dps)"""
    )

    with open("/app/pipeline.py", "w") as f:
        f.write(content)


def main():
    patch_pipeline()
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


if __name__ == "__main__":
    main()
