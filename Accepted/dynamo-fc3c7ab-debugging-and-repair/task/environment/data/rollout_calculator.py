"""
Rollout Calculator Module
=========================
Computes deterministic rollout assignment for device-flag pairs.
Uses a hash-based bucketing approach to ensure stable, repeatable
assignment decisions. The hash produces a value in [0, 100] which
is compared against the flag's rollout percentage threshold.

Supports gradual rollout with configurable percentage targets.
"""

import hashlib
from typing import Optional


def compute_hash(device_id: str, flag_name: str) -> float:
    """
    Compute a deterministic hash value in [0, 100] for a device-flag pair.

    The hash combines device_id and flag_name to produce independent
    bucketing per flag. This ensures that a device at the 45th percentile
    for one flag may be at the 78th percentile for another flag.

    Args:
        device_id: Unique device identifier.
        flag_name: Name of the feature flag being evaluated.

    Returns:
        Float value in range [0, 100] representing the device's bucket position.
    """
    # Combine device_id and flag_name for per-flag independent bucketing
    composite_key = f"{device_id}:{flag_name}"
    hash_bytes = hashlib.sha256(composite_key.encode("utf-8")).hexdigest()

    # Take first 8 hex chars (32 bits) and map to [0, 100]
    hash_int = int(hash_bytes[:8], 16)
    bucket_value = (hash_int % 10000) / 100.0

    return round(bucket_value, 2)


def evaluate_rollout(device_id: str, flag_name: str, rollout_percentage: float,
                     hash_value: Optional[float] = None) -> dict:
    """
    Determine if a device is included in a flag's rollout cohort.

    Args:
        device_id: Unique device identifier.
        flag_name: Name of the feature flag.
        rollout_percentage: Target percentage (0-100) of devices to include.
        hash_value: Pre-computed hash value (if None, computed internally).

    Returns:
        Dictionary with 'included' (bool), 'hash_value' (float),
        and 'threshold' (float) fields.
    """
    if rollout_percentage <= 0:
        return {
            "included": False,
            "hash_value": 0.0,
            "threshold": rollout_percentage,
            "reason": "rollout_disabled",
        }

    if rollout_percentage >= 100:
        return {
            "included": True,
            "hash_value": 0.0,
            "threshold": rollout_percentage,
            "reason": "full_rollout",
        }

    # Compute hash if not provided
    if hash_value is None:
        hash_value = compute_hash(device_id, flag_name)

    included = hash_value < rollout_percentage

    return {
        "included": included,
        "hash_value": hash_value,
        "threshold": rollout_percentage,
        "reason": "rollout" if included else "rollout_excluded",
    }


def compute_cohort_stats(devices: list, flag_name: str, rollout_percentage: float) -> dict:
    """
    Compute rollout cohort statistics for a set of devices.

    Args:
        devices: List of device record dictionaries.
        flag_name: Name of the feature flag.
        rollout_percentage: Target rollout percentage.

    Returns:
        Dictionary with cohort statistics.
    """
    included_count = 0
    excluded_count = 0
    hash_values = []

    for device in devices:
        device_id = device["device_id"]
        result = evaluate_rollout(device_id, flag_name, rollout_percentage)
        hash_values.append(result["hash_value"])
        if result["included"]:
            included_count += 1
        else:
            excluded_count += 1

    total = len(devices)
    actual_percentage = (included_count / total * 100) if total > 0 else 0

    return {
        "total_devices": total,
        "included": included_count,
        "excluded": excluded_count,
        "target_percentage": rollout_percentage,
        "actual_percentage": round(actual_percentage, 2),
        "deviation": round(abs(actual_percentage - rollout_percentage), 2),
    }


def get_hash_method_name() -> str:
    """Return the name of the hashing method used for rollout computation."""
    return "device_flag_composite"
