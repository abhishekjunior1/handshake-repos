"""
Migration planning engine for storage tiering.

Generates optimal block migration plans that respect bandwidth and
IOPS budgets while maximizing tier alignment improvement. Plans
are bounded by configurable migration window constraints to avoid
overwhelming the storage fabric.
"""

from typing import Any


# Default migration constraints
DEFAULT_MAX_MIGRATIONS = 100
DEFAULT_BANDWIDTH_LIMIT_MB = 500  # MB per migration window
DEFAULT_IOPS_BUDGET = 5000


def compute_migration_cost(source_tier_type: str, target_tier_type: str,
                           block_count: int) -> dict[str, float]:
    """
    Compute the I/O cost of migrating blocks between tiers.

    Cross-tier migrations have different costs based on source/target:
    - SSD→HDD: fast read, slow write
    - HDD→SSD: slow read, fast write
    - Any→Archive: slow write (tape/cold)
    """
    # IOPS cost per block based on tier combination
    iops_costs = {
        ("ssd", "hdd"): 2.0,      # fast read + slow write
        ("hdd", "ssd"): 3.0,      # slow read + fast write (GC overhead)
        ("ssd", "archive"): 1.5,  # fast read + sequential write
        ("archive", "ssd"): 4.0,  # slow read + random write
        ("hdd", "archive"): 1.0,  # sequential both
        ("archive", "hdd"): 2.5,  # slow read + moderate write
    }

    # Bandwidth cost (MB per block, 4K blocks)
    bandwidth_per_block_mb = 4.0 / 1024.0  # 4KB = 0.00390625 MB

    iops_per_block = iops_costs.get((source_tier_type, target_tier_type), 2.0)

    return {
        "total_iops": iops_per_block * block_count,
        "total_bandwidth_mb": bandwidth_per_block_mb * block_count,
        "iops_per_block": iops_per_block,
    }


def generate_migration_plan(promote_list: list[dict],
                            demote_list: list[dict],
                            tier_map: dict[str, dict],
                            current_placements: dict[str, str],
                            config: dict) -> list[dict]:
    """
    Generate a bounded migration plan from scored promote/demote lists.

    Respects bandwidth and IOPS budgets. Prioritizes promotions
    (hot blocks on slow tiers) over demotions (cold blocks on fast tiers).

    Args:
        promote_list: blocks to promote (sorted by priority)
        demote_list: blocks to demote (sorted by priority)
        tier_map: tier configuration mapping
        current_placements: current block-to-tier assignments
        config: migration constraints (max_migrations, bandwidth_limit_mb, iops_budget)

    Returns:
        Ordered list of migration operations.
    """
    max_migrations = config.get("max_migrations", DEFAULT_MAX_MIGRATIONS)
    bandwidth_limit = config.get("bandwidth_limit_mb", DEFAULT_BANDWIDTH_LIMIT_MB)
    iops_budget = config.get("iops_budget", DEFAULT_IOPS_BUDGET)

    tier_types = {tid: info["tier_type"] for tid, info in tier_map.items()}

    # Heat label → target tier type
    heat_to_tier_type = {"hot": "ssd", "warm": "hdd", "cold": "archive"}

    # Find tier_id for each tier_type
    tier_type_to_id = {}
    for tid, info in tier_map.items():
        tier_type_to_id[info["tier_type"]] = tid

    migrations = []
    total_bandwidth = 0.0
    total_iops = 0.0

    # Process promotions first (higher priority)
    for block in promote_list:
        if len(migrations) >= max_migrations:
            break

        block_key = block["block_key"]
        source_tier = current_placements.get(block_key, "unknown")
        source_type = tier_types.get(source_tier, "hdd")
        target_type = heat_to_tier_type.get(block["heat_label"], "hdd")
        target_tier = tier_type_to_id.get(target_type)

        if target_tier is None or source_tier == target_tier:
            continue

        cost = compute_migration_cost(source_type, target_type, 1)

        # Check budget constraints
        if (total_bandwidth + cost["total_bandwidth_mb"] > bandwidth_limit or
                total_iops + cost["total_iops"] > iops_budget):
            continue

        migrations.append({
            "block_key": block_key,
            "source_tier": source_tier,
            "target_tier": target_tier,
            "action": "promote",
            "priority_score": block["decayed_score"],
            "iops_cost": cost["total_iops"],
            "bandwidth_mb": cost["total_bandwidth_mb"],
            "block_count": 1,
        })
        total_bandwidth += cost["total_bandwidth_mb"]
        total_iops += cost["total_iops"]

    # Process demotions
    for block in demote_list:
        if len(migrations) >= max_migrations:
            break

        block_key = block["block_key"]
        source_tier = current_placements.get(block_key, "unknown")
        source_type = tier_types.get(source_tier, "hdd")
        target_type = heat_to_tier_type.get(block["heat_label"], "archive")
        target_tier = tier_type_to_id.get(target_type)

        if target_tier is None or source_tier == target_tier:
            continue

        cost = compute_migration_cost(source_type, target_type, 1)

        if (total_bandwidth + cost["total_bandwidth_mb"] > bandwidth_limit or
                total_iops + cost["total_iops"] > iops_budget):
            continue

        migrations.append({
            "block_key": block_key,
            "source_tier": source_tier,
            "target_tier": target_tier,
            "action": "demote",
            "priority_score": block["decayed_score"],
            "iops_cost": cost["total_iops"],
            "bandwidth_mb": cost["total_bandwidth_mb"],
            "block_count": 1,
        })
        total_bandwidth += cost["total_bandwidth_mb"]
        total_iops += cost["total_iops"]

    return migrations


def summarize_migration_plan(migrations: list[dict]) -> dict[str, Any]:
    """
    Summarize migration plan statistics.

    Returns aggregate metrics about the planned migrations.
    """
    if not migrations:
        return {
            "total_migrations": 0,
            "promotions": 0,
            "demotions": 0,
            "total_iops_cost": 0.0,
            "total_bandwidth_mb": 0.0,
            "avg_priority_score": 0.0,
        }

    promotions = [m for m in migrations if m["action"] == "promote"]
    demotions = [m for m in migrations if m["action"] == "demote"]

    total_iops = sum(m["iops_cost"] for m in migrations)
    total_bw = sum(m["bandwidth_mb"] for m in migrations)
    avg_priority = sum(m["priority_score"] for m in migrations) / len(migrations)

    return {
        "total_migrations": len(migrations),
        "promotions": len(promotions),
        "demotions": len(demotions),
        "total_iops_cost": round(total_iops, 2),
        "total_bandwidth_mb": round(total_bw, 6),
        "avg_priority_score": round(avg_priority, 4),
    }
