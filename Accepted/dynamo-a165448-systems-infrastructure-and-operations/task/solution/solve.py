"""
Solution for the storage tiering engine pipeline.

Fixes two bugs in pipeline.py:
1. Uses per-tier classification thresholds instead of global thresholds
2. Uses interval write blocks instead of cumulative for wear rate calculation

Then runs the fixed pipeline to produce output.json.
"""

import subprocess
import os


def apply_fixes():
    """Apply string-replacement patches to pipeline.py."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, "r") as f:
        content = f.read()

    # Fix 1: Replace global threshold usage with per-tier threshold logic
    # The buggy code uses a single global threshold for all blocks.
    # The fix classifies each block using its tier's specific thresholds.
    old_classification = '''    # Apply global classification threshold from config for uniform evaluation
    global_thresholds = {
        "hot_threshold": config["global_hot_threshold"],
        "warm_threshold": config["global_warm_threshold"],
    }
    classifications = classify_all_blocks(
        block_stats, observation_window, current_time, epoch_length,
        global_thresholds
    )'''

    new_classification = '''    # Classify blocks using per-tier thresholds based on current placement
    device_to_tier = {}
    for tier_id, tier_info in tier_map.items():
        for dev_id in tier_info["devices"]:
            device_to_tier[dev_id] = tier_id

    classifications = {}
    for block_key, stats in block_stats.items():
        dev_id = stats["device_id"]
        tier_id = device_to_tier.get(dev_id, list(tier_thresholds.keys())[0])
        tier_thresh = tier_thresholds[tier_id]
        single_block = {block_key: stats}
        block_class = classify_all_blocks(
            single_block, observation_window, current_time, epoch_length,
            tier_thresh
        )
        classifications.update(block_class)'''

    content = content.replace(old_classification, new_classification)

    # Fix 2: Use interval_write_blocks instead of total_write_blocks for rate
    old_wear = '''        # Use cumulative write count for lifecycle tracking continuity —
        # this provides a monotonically increasing baseline for endurance
        # projection rather than per-interval snapshots that fluctuate.
        write_blocks_for_rate = dev_writes.get(
            "total_write_blocks",
            dev_writes.get("interval_write_blocks", 0)
        )'''

    new_wear = '''        # Use interval write blocks for current wear rate calculation
        write_blocks_for_rate = dev_writes.get(
            "interval_write_blocks",
            dev_writes.get("total_write_blocks", 0)
        )'''

    content = content.replace(old_wear, new_wear)

    with open(pipeline_path, "w") as f:
        f.write(content)


def run_pipeline():
    """Execute the fixed pipeline."""
    subprocess.run(
        ["python3", "/app/pipeline.py", "/app/storage_config.json", "/app/output.json"],
        check=True,
        cwd="/app",
    )


if __name__ == "__main__":
    apply_fixes()
    run_pipeline()
