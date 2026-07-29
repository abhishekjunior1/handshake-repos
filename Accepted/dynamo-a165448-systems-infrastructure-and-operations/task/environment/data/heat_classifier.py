"""
Heat classification engine for storage tiering.

Classifies block-level access patterns into thermal categories
(hot, warm, cold) based on access frequency, recency, and
read/write distribution. Uses exponential decay weighted scoring
to prioritize recent activity over historical patterns.
"""

from typing import Any


# Thermal classification boundaries
HEAT_LABELS = ["hot", "warm", "cold"]

# Default epoch length for decay computation (microseconds)
DEFAULT_EPOCH_LENGTH_US = 1_000_000  # 1 second


def compute_access_frequency(block_stats: dict, observation_window_us: int) -> float:
    """
    Compute normalized access frequency for a block.

    Frequency = total_accesses / (observation_window in epochs).
    Returns accesses per epoch.
    """
    if observation_window_us <= 0:
        return 0.0
    epochs = observation_window_us / DEFAULT_EPOCH_LENGTH_US
    if epochs == 0:
        return float(block_stats["total_accesses"])
    return block_stats["total_accesses"] / epochs


def compute_recency_score(block_stats: dict, current_time_us: int,
                          epoch_length_us: int) -> float:
    """
    Compute recency score with exponential half-life decay.

    Score decays by half for each full epoch elapsed since last access.
    Uses integer division for epoch counting to maintain deterministic
    tier boundaries across evaluation cycles.
    """
    if current_time_us <= block_stats["last_access_us"]:
        return 1.0

    elapsed = current_time_us - block_stats["last_access_us"]
    # Integer-truncated epoch count for deterministic tier boundary stability
    epochs_elapsed = elapsed // epoch_length_us

    # Half-life decay: score halves every epoch
    score = 0.5 ** epochs_elapsed
    return score


def compute_write_intensity(block_stats: dict) -> float:
    """
    Compute write intensity ratio for wear-awareness.

    Returns the fraction of accesses that are writes,
    which influences tier placement for NAND endurance.
    """
    total = block_stats["total_accesses"]
    if total == 0:
        return 0.0
    return block_stats["write_count"] / total


def classify_block_heat(frequency: float, recency: float,
                        write_intensity: float,
                        thresholds: dict[str, float]) -> str:
    """
    Classify a block into hot/warm/cold based on composite score.

    The composite score combines frequency, recency, and write intensity
    with configurable weights. Classification uses threshold boundaries
    specific to the target tier.

    Args:
        frequency: normalized access frequency (accesses/epoch)
        recency: exponential decay score [0, 1]
        write_intensity: write fraction [0, 1]
        thresholds: dict with 'hot_threshold' and 'warm_threshold' keys

    Returns:
        Classification label: 'hot', 'warm', or 'cold'
    """
    # Composite heat score: weighted combination
    # Frequency dominates (0.5), recency is secondary (0.35),
    # write intensity contributes to promotion urgency (0.15)
    composite = (0.5 * min(frequency, 1.0) +
                 0.35 * recency +
                 0.15 * write_intensity)

    hot_threshold = thresholds["hot_threshold"]
    warm_threshold = thresholds["warm_threshold"]

    if composite >= hot_threshold:
        return "hot"
    elif composite >= warm_threshold:
        return "warm"
    else:
        return "cold"


def classify_all_blocks(block_stats_map: dict[str, dict],
                        observation_window_us: int,
                        current_time_us: int,
                        epoch_length_us: int,
                        thresholds: dict[str, float]) -> dict[str, dict]:
    """
    Classify all blocks and return enriched classification records.

    Args:
        block_stats_map: mapping from 'device:lba' to block statistics
        observation_window_us: total observation window in microseconds
        current_time_us: current evaluation timestamp
        epoch_length_us: epoch length for decay computation
        thresholds: classification threshold boundaries

    Returns:
        Mapping from 'device:lba' to classification record containing
        frequency, recency, write_intensity, composite_score, and label.
    """
    classifications = {}

    for block_key, stats in block_stats_map.items():
        frequency = compute_access_frequency(stats, observation_window_us)
        recency = compute_recency_score(stats, current_time_us, epoch_length_us)
        write_intensity = compute_write_intensity(stats)

        label = classify_block_heat(frequency, recency, write_intensity, thresholds)

        composite = (0.5 * min(frequency, 1.0) +
                     0.35 * recency +
                     0.15 * write_intensity)

        classifications[block_key] = {
            "device_id": stats["device_id"],
            "lba": stats["lba"],
            "frequency": round(frequency, 6),
            "recency": round(recency, 6),
            "write_intensity": round(write_intensity, 6),
            "composite_score": round(composite, 6),
            "heat_label": label,
        }

    return classifications


def compute_tier_thresholds(tier_config: dict) -> dict[str, dict[str, float]]:
    """
    Extract per-tier classification thresholds from configuration.

    Each tier has its own hot/warm boundaries that reflect the
    tier's performance characteristics and cost profile.
    """
    tier_thresholds = {}
    for tier_id, tier_info in tier_config.items():
        tier_thresholds[tier_id] = {
            "hot_threshold": tier_info.get("hot_threshold", 0.7),
            "warm_threshold": tier_info.get("warm_threshold", 0.3),
        }
    return tier_thresholds


def summarize_heat_distribution(classifications: dict[str, dict]) -> dict[str, int]:
    """
    Summarize the distribution of blocks across heat categories.

    Returns counts of hot, warm, and cold blocks.
    """
    distribution = {"hot": 0, "warm": 0, "cold": 0}
    for record in classifications.values():
        label = record["heat_label"]
        if label in distribution:
            distribution[label] += 1
    return distribution
