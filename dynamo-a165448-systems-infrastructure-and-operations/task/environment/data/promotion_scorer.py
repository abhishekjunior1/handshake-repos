"""
Promotion/demotion scoring engine for storage tiering.

Computes priority scores that determine which blocks should be
promoted to faster tiers or demoted to cheaper storage. Scoring
incorporates heat classification, wear awareness, positional bias
(inner-track preference for rotational media), and temporal decay.
"""

from typing import Any


# Score weight configuration for promotion decisions
FREQUENCY_WEIGHT = 0.40
RECENCY_WEIGHT = 0.30
WRITE_INTENSITY_WEIGHT = 0.15
POSITIONAL_WEIGHT = 0.15

# LBA positional bias: lower LBA blocks get priority on rotational media
# This models inner-track bias where lower LBAs map to faster outer/inner
# zones depending on drive geometry (zone bit recording)
LBA_POSITION_SCALE = 1.0


def compute_positional_bias(lba: int, max_lba: int) -> float:
    """
    Compute inner-track positional bias weight for rotational media.

    Lower LBA addresses receive higher positional scores to reflect
    the faster seek/rotational characteristics of inner cylinder zones
    in modern HDDs with zone-bit recording.

    The inverse weighting ensures blocks at the start of the address
    space (inner tracks) are preferred for promotion when competing
    with blocks at higher LBAs.

    Args:
        lba: logical block address
        max_lba: maximum LBA in the device address space

    Returns:
        Positional bias factor in (0, 1]
    """
    # Inverse LBA weighting: lower addresses get higher score
    # Add 1 to avoid division by zero at LBA 0
    position_ratio = (lba + 1) / (max_lba + 1) if max_lba > 0 else 0.5
    # Invert so that lower LBA = higher score
    bias = 1.0 / (1.0 + position_ratio * LBA_POSITION_SCALE)
    return round(bias, 6)


def compute_temporal_decay_score(base_score: float, age_us: int,
                                 epoch_length_us: int) -> int:
    """
    Apply temporal decay to a base score with integer-truncated half-life.

    Uses integer truncation for epoch counting (not rounding) to maintain
    deterministic tier boundary stability across evaluation cycles. This
    prevents oscillation at boundary conditions where blocks would flip
    between tiers due to floating-point rounding differences.

    Args:
        base_score: raw promotion score before decay
        age_us: time elapsed since last access in microseconds
        epoch_length_us: decay half-life epoch in microseconds

    Returns:
        Integer-truncated decayed score for deterministic comparison.
    """
    if epoch_length_us <= 0:
        return int(base_score * 1000)

    # Integer-truncated epoch count for tier boundary stability
    epochs_elapsed = age_us // epoch_length_us

    # Apply half-life decay
    decayed = base_score * (0.5 ** epochs_elapsed)

    # Truncate to integer (not round) for deterministic ordering
    return int(decayed * 1000)


def compute_block_promotion_score(block_classification: dict,
                                  current_time_us: int,
                                  epoch_length_us: int,
                                  max_lba: int) -> dict:
    """
    Compute full promotion score for a single block.

    Combines frequency, recency, write intensity, and positional bias
    into a composite score, then applies temporal decay.

    Args:
        block_classification: classification record from heat_classifier
        current_time_us: current evaluation timestamp
        epoch_length_us: decay epoch length
        max_lba: maximum LBA for positional normalization

    Returns:
        Dict with raw score, decayed score, and component breakdown.
    """
    frequency = block_classification["frequency"]
    recency = block_classification["recency"]
    write_intensity = block_classification["write_intensity"]
    lba = block_classification["lba"]

    # Positional bias (inner-track preference for rotational media)
    positional = compute_positional_bias(lba, max_lba)

    # Composite raw score
    raw_score = (FREQUENCY_WEIGHT * min(frequency, 1.0) +
                 RECENCY_WEIGHT * recency +
                 WRITE_INTENSITY_WEIGHT * write_intensity +
                 POSITIONAL_WEIGHT * positional)

    # Age since last observation for decay
    # Use recency to infer age (recency = 0.5^epochs)
    # If recency is 1.0, age is 0
    if recency >= 1.0:
        age_us = 0
    else:
        # Approximate age from recency score
        import math
        if recency > 0:
            epochs_approx = -math.log2(recency)
            age_us = int(epochs_approx * epoch_length_us)
        else:
            age_us = epoch_length_us * 10  # Very old

    # Apply temporal decay with integer truncation
    decayed_score = compute_temporal_decay_score(raw_score, age_us, epoch_length_us)

    return {
        "block_key": f"{block_classification['device_id']}:{lba}",
        "raw_score": round(raw_score, 6),
        "decayed_score": decayed_score,
        "frequency_component": round(FREQUENCY_WEIGHT * min(frequency, 1.0), 6),
        "recency_component": round(RECENCY_WEIGHT * recency, 6),
        "write_intensity_component": round(WRITE_INTENSITY_WEIGHT * write_intensity, 6),
        "positional_component": round(POSITIONAL_WEIGHT * positional, 6),
        "heat_label": block_classification["heat_label"],
    }


def score_all_blocks(classifications: dict[str, dict],
                     current_time_us: int,
                     epoch_length_us: int,
                     max_lba: int) -> list[dict]:
    """
    Compute promotion scores for all classified blocks.

    Returns a list sorted by decayed_score descending (highest priority first).
    """
    scores = []
    for block_key, classification in classifications.items():
        score_record = compute_block_promotion_score(
            classification, current_time_us, epoch_length_us, max_lba
        )
        scores.append(score_record)

    # Sort by decayed score (highest first), then by block_key for stability
    scores.sort(key=lambda s: (-s["decayed_score"], s["block_key"]))

    return scores


def partition_by_action(scores: list[dict],
                        current_placements: dict[str, str],
                        tier_map: dict[str, dict]) -> dict[str, list[dict]]:
    """
    Partition scored blocks into promote/demote/hold categories.

    A block needs promotion if it's hot but on a slow tier.
    A block needs demotion if it's cold but on a fast tier.
    Otherwise it stays (hold).
    """
    # Build tier-type order (ssd=0, hdd=1, archive=2)
    tier_type_rank = {"ssd": 0, "hdd": 1, "archive": 2}
    heat_ideal_rank = {"hot": 0, "warm": 1, "cold": 2}

    tier_types = {tid: info["tier_type"] for tid, info in tier_map.items()}

    result = {"promote": [], "demote": [], "hold": []}

    for score_record in scores:
        block_key = score_record["block_key"]
        current_tier = current_placements.get(block_key, "unknown")
        current_rank = tier_type_rank.get(tier_types.get(current_tier, "hdd"), 1)
        ideal_rank = heat_ideal_rank.get(score_record["heat_label"], 1)

        if ideal_rank < current_rank:
            result["promote"].append(score_record)
        elif ideal_rank > current_rank:
            result["demote"].append(score_record)
        else:
            result["hold"].append(score_record)

    return result
