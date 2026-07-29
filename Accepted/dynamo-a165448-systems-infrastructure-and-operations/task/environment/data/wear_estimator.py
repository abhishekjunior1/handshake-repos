"""
NAND wear leveling estimator for SSD tier management.

Estimates flash endurance consumption based on write amplification
factor (WAF), program/erase cycle counts, and capacity utilization.
Produces wear metrics that inform tier promotion decisions — blocks
with high write intensity should avoid heavily-worn SSD tiers.
"""

from typing import Any
import math


# Industry-standard TBW (terabytes written) per TB of NAND capacity
# for enterprise-grade TLC NAND (conservative estimate)
DEFAULT_TBW_PER_TB = 1800

# Write amplification model parameters
# WAF increases with utilization due to garbage collection overhead
WAF_BASE = 1.0
WAF_UTILIZATION_COEFFICIENT = 2.5


def compute_write_amplification(used_capacity_blocks: int,
                                total_capacity_blocks: int,
                                over_provision_ratio: float = 1.0) -> float:
    """
    Compute write amplification factor (WAF) based on capacity utilization.

    WAF models the additional writes caused by garbage collection in NAND.
    Higher utilization means more GC overhead, increasing effective writes.

    The model uses:
      WAF = base + coefficient * (used / effective_capacity)^2

    where effective_capacity accounts for over-provisioning.

    Args:
        used_capacity_blocks: blocks currently allocated/written
        total_capacity_blocks: total physical blocks available
        over_provision_ratio: ratio of physical to logical capacity

    Returns:
        Write amplification factor >= 1.0
    """
    if total_capacity_blocks <= 0:
        return WAF_BASE

    effective_capacity = total_capacity_blocks / over_provision_ratio
    if effective_capacity <= 0:
        return WAF_BASE

    utilization = min(used_capacity_blocks / effective_capacity, 1.0)
    waf = WAF_BASE + WAF_UTILIZATION_COEFFICIENT * (utilization ** 2)

    return round(waf, 4)


def estimate_endurance_consumed(write_blocks: int,
                                waf: float,
                                capacity_blocks: int,
                                block_size_bytes: int = 4096) -> float:
    """
    Estimate fraction of NAND endurance consumed.

    Converts block writes to TBW equivalent using WAF, then divides
    by rated TBW capacity to get endurance fraction.

    Args:
        write_blocks: number of logical blocks written
        waf: write amplification factor
        capacity_blocks: capacity used for TBW rating calculation
        block_size_bytes: bytes per block (default 4K)

    Returns:
        Endurance consumed as fraction [0.0, 1.0+]
        Values > 1.0 indicate exceeding rated endurance.
    """
    if capacity_blocks <= 0 or waf <= 0:
        return 0.0

    # Actual physical bytes written (including amplification)
    physical_bytes_written = write_blocks * block_size_bytes * waf

    # Convert to terabytes
    physical_tb_written = physical_bytes_written / (1024 ** 4)

    # Rated TBW for this capacity
    capacity_tb = (capacity_blocks * block_size_bytes) / (1024 ** 4)
    rated_tbw = capacity_tb * DEFAULT_TBW_PER_TB

    if rated_tbw <= 0:
        return 0.0

    endurance_consumed = physical_tb_written / rated_tbw

    return round(endurance_consumed, 8)


def compute_wear_rate(write_blocks_per_interval: int,
                      waf: float,
                      capacity_blocks: int,
                      interval_duration_us: int,
                      block_size_bytes: int = 4096) -> float:
    """
    Compute instantaneous wear rate (endurance fraction per second).

    Uses interval write volume (not cumulative) to compute the
    current rate of endurance consumption. This enables projection
    of remaining useful life.

    Args:
        write_blocks_per_interval: blocks written in the current interval
        waf: current write amplification factor
        capacity_blocks: capacity for TBW calculation
        interval_duration_us: interval length in microseconds
        block_size_bytes: bytes per block

    Returns:
        Wear rate in endurance-fraction per second.
    """
    if interval_duration_us <= 0 or capacity_blocks <= 0:
        return 0.0

    interval_endurance = estimate_endurance_consumed(
        write_blocks_per_interval, waf, capacity_blocks, block_size_bytes
    )

    interval_seconds = interval_duration_us / 1_000_000.0
    if interval_seconds <= 0:
        return 0.0

    return round(interval_endurance / interval_seconds, 12)


def estimate_remaining_life_hours(current_endurance_consumed: float,
                                  wear_rate_per_second: float) -> float:
    """
    Estimate remaining device life in hours.

    Projects when endurance will reach 100% at current wear rate.
    Returns float('inf') if wear rate is zero.
    """
    if wear_rate_per_second <= 0:
        return float("inf")

    remaining_endurance = max(0.0, 1.0 - current_endurance_consumed)
    remaining_seconds = remaining_endurance / wear_rate_per_second
    remaining_hours = remaining_seconds / 3600.0

    return round(remaining_hours, 2)


def compute_wear_metrics(device_id: str,
                         write_blocks_interval: int,
                         write_blocks_cumulative: int,
                         capacity_blocks: int,
                         over_provision_ratio: float,
                         interval_duration_us: int) -> dict[str, Any]:
    """
    Compute comprehensive wear metrics for a device.

    This is the main entry point called by the orchestrator.
    It computes WAF, endurance consumed, wear rate, and remaining life.

    Args:
        device_id: device identifier
        write_blocks_interval: blocks written in current interval
        write_blocks_cumulative: total cumulative blocks written
        capacity_blocks: capacity for utilization and TBW calculation
        over_provision_ratio: over-provisioning factor
        interval_duration_us: current interval duration in microseconds

    Returns:
        Dict with wear metrics for this device.
    """
    # WAF depends on utilization (how full the device is)
    waf = compute_write_amplification(
        write_blocks_cumulative, capacity_blocks, over_provision_ratio
    )

    # Endurance consumed based on cumulative writes
    endurance_consumed = estimate_endurance_consumed(
        write_blocks_cumulative, waf, capacity_blocks
    )

    # Current wear rate based on interval writes
    wear_rate = compute_wear_rate(
        write_blocks_interval, waf, capacity_blocks, interval_duration_us
    )

    # Remaining life projection
    remaining_life_h = estimate_remaining_life_hours(endurance_consumed, wear_rate)

    return {
        "device_id": device_id,
        "write_amplification_factor": waf,
        "endurance_consumed_fraction": endurance_consumed,
        "wear_rate_per_second": wear_rate,
        "remaining_life_hours": remaining_life_h,
        "capacity_blocks_used_for_calc": capacity_blocks,
        "interval_write_blocks": write_blocks_interval,
        "cumulative_write_blocks": write_blocks_cumulative,
    }
