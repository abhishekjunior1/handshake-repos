"""
Tier mapping engine for block-to-device assignment.

Manages the logical-to-physical mapping between blocks and storage
tiers, tracks tier capacity utilization, and validates placement
constraints. Supports multi-tier architectures with configurable
capacity limits and over-provisioning ratios.
"""

from typing import Any


def build_tier_map(devices: list[dict], tiers: list[dict]) -> dict[str, dict]:
    """
    Build the tier-to-device mapping from configuration.

    Returns a mapping from tier_id to tier metadata including:
      - tier_id: unique tier identifier
      - tier_type: 'ssd', 'hdd', or 'archive'
      - devices: list of device_ids in this tier
      - total_capacity_blocks: total capacity across all devices
      - used_capacity_blocks: currently used capacity
      - over_provision_ratio: SSD over-provisioning factor
    """
    tier_map = {}
    device_lookup = {d["device_id"]: d for d in devices}

    for tier in tiers:
        tier_id = tier["tier_id"]
        tier_devices = tier["device_ids"]

        total_capacity = 0
        used_capacity = 0
        for dev_id in tier_devices:
            dev = device_lookup[dev_id]
            total_capacity += dev["capacity_blocks"]
            used_capacity += dev.get("used_blocks", 0)

        tier_map[tier_id] = {
            "tier_id": tier_id,
            "tier_type": tier["tier_type"],
            "devices": tier_devices,
            "total_capacity_blocks": total_capacity,
            "used_capacity_blocks": used_capacity,
            "over_provision_ratio": tier.get("over_provision_ratio", 1.0),
            "hot_threshold": tier.get("hot_threshold", 0.7),
            "warm_threshold": tier.get("warm_threshold", 0.3),
        }

    return tier_map


def get_current_block_placement(block_stats: dict[str, dict],
                                tier_map: dict[str, dict]) -> dict[str, str]:
    """
    Determine current tier placement for each block.

    Maps each 'device:lba' key to the tier that contains its device.
    """
    device_to_tier = {}
    for tier_id, tier_info in tier_map.items():
        for dev_id in tier_info["devices"]:
            device_to_tier[dev_id] = tier_id

    placements = {}
    for block_key, stats in block_stats.items():
        dev_id = stats["device_id"]
        placements[block_key] = device_to_tier.get(dev_id, "unknown")

    return placements


def compute_tier_utilization(tier_map: dict[str, dict]) -> dict[str, dict]:
    """
    Compute utilization metrics for each tier.

    Returns mapping from tier_id to:
      - utilization_pct: used/total as percentage
      - available_blocks: remaining capacity
      - effective_capacity: usable capacity after over-provisioning
    """
    utilization = {}
    for tier_id, tier_info in tier_map.items():
        total = tier_info["total_capacity_blocks"]
        used = tier_info["used_capacity_blocks"]
        op_ratio = tier_info["over_provision_ratio"]

        # Effective capacity accounts for over-provisioning reserve
        effective = int(total / op_ratio)
        available = max(0, effective - used)
        util_pct = (used / effective * 100.0) if effective > 0 else 0.0

        utilization[tier_id] = {
            "tier_id": tier_id,
            "total_capacity_blocks": total,
            "used_capacity_blocks": used,
            "effective_capacity_blocks": effective,
            "available_blocks": available,
            "utilization_pct": round(util_pct, 2),
        }

    return utilization


def validate_migration_capacity(tier_map: dict[str, dict],
                                migrations: list[dict]) -> list[dict]:
    """
    Validate that proposed migrations don't exceed tier capacity.

    Filters out migrations that would cause target tier overflow.
    Returns only valid migrations that fit within capacity constraints.
    """
    # Track projected capacity changes
    capacity_changes: dict[str, int] = {}
    for tier_id in tier_map:
        capacity_changes[tier_id] = 0

    valid_migrations = []
    for migration in migrations:
        target_tier = migration["target_tier"]
        source_tier = migration["source_tier"]
        blocks = migration.get("block_count", 1)

        tier_info = tier_map[target_tier]
        effective = int(tier_info["total_capacity_blocks"] /
                       tier_info["over_provision_ratio"])
        current_used = tier_info["used_capacity_blocks"] + capacity_changes[target_tier]

        if current_used + blocks <= effective:
            capacity_changes[target_tier] += blocks
            capacity_changes[source_tier] -= blocks
            valid_migrations.append(migration)

    return valid_migrations


def compute_tier_balance_score(tier_map: dict[str, dict],
                               classifications: dict[str, dict],
                               placements: dict[str, str]) -> float:
    """
    Compute how well current placements match heat classifications.

    A score of 1.0 means all hot blocks are on SSD, all cold on archive.
    Lower scores indicate misplaced blocks needing migration.
    """
    if not classifications:
        return 1.0

    correct_placements = 0
    total_blocks = len(classifications)

    # Ideal tier mapping: hot→ssd, warm→hdd, cold→archive
    ideal_mapping = {"hot": "ssd", "warm": "hdd", "cold": "archive"}

    # Build tier_type lookup
    tier_types = {tid: info["tier_type"] for tid, info in tier_map.items()}

    for block_key, classification in classifications.items():
        ideal_type = ideal_mapping.get(classification["heat_label"], "hdd")
        current_tier = placements.get(block_key, "unknown")
        current_type = tier_types.get(current_tier, "unknown")

        if current_type == ideal_type:
            correct_placements += 1

    return round(correct_placements / total_blocks, 4) if total_blocks > 0 else 1.0
