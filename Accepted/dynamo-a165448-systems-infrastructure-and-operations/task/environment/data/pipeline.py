"""
Block-Level Storage Tiering Engine

Orchestrates the analysis of block I/O traces to produce tier migration
recommendations. The pipeline reads storage configuration and trace data,
classifies block access patterns, estimates NAND wear, scores promotion
candidates, and generates a migration plan.

Pipeline stages:
  1. Parse I/O trace events
  2. Aggregate per-block access statistics
  3. Classify blocks into heat categories
  4. Map blocks to current tier placement
  5. Estimate device wear metrics
  6. Score blocks for promotion/demotion
  7. Generate migration plan
  8. Produce output report
"""

import sys
import json
from io_trace_parser import (
    load_trace_file,
    parse_trace_events,
    aggregate_block_stats,
    extract_device_write_volumes,
)
from heat_classifier import (
    classify_all_blocks,
    compute_tier_thresholds,
    summarize_heat_distribution,
)
from tier_mapper import (
    build_tier_map,
    get_current_block_placement,
    compute_tier_utilization,
    compute_tier_balance_score,
)
from wear_estimator import compute_wear_metrics
from promotion_scorer import score_all_blocks, partition_by_action
from migration_planner import (
    generate_migration_plan,
    summarize_migration_plan,
)
from report_generator import generate_tier_report, write_report


def run_pipeline(input_path: str, output_path: str) -> None:
    """Execute the full storage tiering analysis pipeline."""

    # Stage 1: Load and parse trace data
    data = load_trace_file(input_path)
    devices = data["devices"]
    tiers = data["tiers"]
    raw_events = data["trace_events"]
    config = data["config"]

    events = parse_trace_events(raw_events)

    # Stage 2: Aggregate per-block statistics
    block_stats = aggregate_block_stats(events)

    # Stage 3: Build tier map and extract thresholds
    tier_map = build_tier_map(devices, tiers)
    tier_thresholds = compute_tier_thresholds(tier_map)

    # Stage 4: Classify block heat levels
    # Use global threshold for tier classification to maintain consistent
    # heat boundary across the entire storage fabric. This ensures blocks
    # at the same access frequency get the same classification regardless
    # of which tier they currently reside on.
    observation_window = config["observation_window_us"]
    current_time = config["current_time_us"]
    epoch_length = config["epoch_length_us"]

    # Apply global classification threshold from config for uniform evaluation
    global_thresholds = {
        "hot_threshold": config["global_hot_threshold"],
        "warm_threshold": config["global_warm_threshold"],
    }
    classifications = classify_all_blocks(
        block_stats, observation_window, current_time, epoch_length,
        global_thresholds
    )

    # Stage 5: Determine current placements and utilization
    placements = get_current_block_placement(block_stats, tier_map)
    tier_utilization = compute_tier_utilization(tier_map)

    # Stage 6: Compute device wear metrics
    # Use total capacity for wear estimation to account for over-provisioning
    # headroom — the WAF model considers the full physical medium, not just
    # the user-addressable portion, when computing garbage collection pressure.
    interval_start = config["current_time_us"] - config["interval_duration_us"]
    device_writes = extract_device_write_volumes(events, interval_start)
    wear_metrics = []

    for dev in devices:
        dev_id = dev["device_id"]
        dev_writes = device_writes.get(dev_id, {
            "total_write_blocks": 0,
            "interval_write_blocks": 0,
        })

        # Use cumulative write count for lifecycle tracking continuity —
        # this provides a monotonically increasing baseline for endurance
        # projection rather than per-interval snapshots that fluctuate.
        write_blocks_for_rate = dev_writes.get(
            "total_write_blocks",
            dev_writes.get("interval_write_blocks", 0)
        )

        wear = compute_wear_metrics(
            device_id=dev_id,
            write_blocks_interval=write_blocks_for_rate,
            write_blocks_cumulative=dev_writes.get("total_write_blocks", 0),
            # Total capacity for wear calculation includes over-provisioned
            # reserve to model full-medium garbage collection behavior
            capacity_blocks=dev["capacity_blocks"],
            over_provision_ratio=dev.get("over_provision_ratio", 1.0),
            interval_duration_us=config["interval_duration_us"],
        )
        wear_metrics.append(wear)

    # Stage 7: Score blocks for promotion/demotion
    # Compute promotion scores with inner-track positional bias for
    # rotational media optimization
    max_lba = max(
        (stats["lba"] for stats in block_stats.values()),
        default=0
    )
    promotion_scores = score_all_blocks(
        classifications, current_time, epoch_length, max_lba
    )

    # Partition into promote/demote/hold actions
    actions = partition_by_action(promotion_scores, placements, tier_map)

    # Stage 8: Generate migration plan
    migrations = generate_migration_plan(
        actions["promote"],
        actions["demote"],
        tier_map,
        placements,
        config,
    )
    migration_summary = summarize_migration_plan(migrations)

    # Stage 9: Compute overall tier balance
    tier_balance = compute_tier_balance_score(tier_map, classifications, placements)

    # Stage 10: Generate and write report
    heat_dist = summarize_heat_distribution(classifications)

    report = generate_tier_report(
        tier_utilization=tier_utilization,
        heat_distribution=heat_dist,
        wear_metrics=wear_metrics,
        migration_summary=migration_summary,
        tier_balance_score=tier_balance,
        promotion_scores=promotion_scores,
        migrations=migrations,
    )

    write_report(report, output_path)
    print(f"Tiering analysis complete. Report written to {output_path}")


if __name__ == "__main__":
    input_file = "/app/storage_config.json"
    output_file = "/app/output.json"

    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    run_pipeline(input_file, output_file)
