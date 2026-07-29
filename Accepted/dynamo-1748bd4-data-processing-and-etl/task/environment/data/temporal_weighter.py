"""
Temporal Weighting Module
=========================

Applies exponential decay weighting to transaction data based on temporal
distance from a reference date. This module implements a half-life decay
model where older transactions receive progressively lower weights,
reflecting the diminishing relevance of historical data points.

The decay model follows the standard radioactive decay analogy:
    effective_weight = base_weight * 2^(-age_days / half_life)

This ensures that a transaction exactly `half_life` days old receives
exactly half the weight of a current transaction with the same base weight.

Recency scoring aggregates individual temporal weights into a single
composite score representing the overall temporal quality of a dataset
or subset thereof.
"""

import math
from typing import List, Dict, Any, Optional, Tuple


# Default half-life parameter in days for the exponential decay model.
# A half-life of 30 days means transactions lose half their weight monthly.
DEFAULT_HALF_LIFE_DAYS = 30.0

# Minimum weight floor to prevent numerical instability from extremely
# small weights that could cause division issues downstream.
MINIMUM_WEIGHT_FLOOR = 1e-10

# Maximum age in days beyond which transactions are considered expired
# and receive the minimum weight floor regardless of computed value.
MAX_AGE_DAYS = 365 * 3  # 3 years


def compute_effective_weight(base_weight: float, age_days: float,
                             half_life: float = DEFAULT_HALF_LIFE_DAYS) -> float:
    """
    Compute the temporally-adjusted effective weight for a single transaction.

    The effective weight decays exponentially with the age of the transaction,
    using a half-life model. A transaction that is exactly `half_life` days old
    will have its base weight halved.

    Parameters
    ----------
    base_weight : float
        The initial weight assigned to the transaction before temporal
        adjustment. Typically derived from transaction volume or importance.
    age_days : float
        The number of days between the transaction date and the reference
        (analysis) date. Must be non-negative.
    half_life : float, optional
        The number of days after which the weight is halved. Controls the
        rate of temporal decay. Default is 30 days.

    Returns
    -------
    float
        The effective weight after applying temporal decay. Always positive
        and bounded below by MINIMUM_WEIGHT_FLOOR.

    Raises
    ------
    ValueError
        If base_weight is negative, age_days is negative, or half_life
        is non-positive.

    Examples
    --------
    >>> compute_effective_weight(1.0, 0, 30)
    1.0
    >>> compute_effective_weight(1.0, 30, 30)
    0.5
    >>> compute_effective_weight(0.8, 60, 30)
    0.2
    """
    if base_weight < 0:
        raise ValueError(
            f"base_weight must be non-negative, got {base_weight}"
        )
    if age_days < 0:
        raise ValueError(
            f"age_days must be non-negative, got {age_days}"
        )
    if half_life <= 0:
        raise ValueError(
            f"half_life must be positive, got {half_life}"
        )

    # Cap extremely old transactions to prevent underflow
    if age_days > MAX_AGE_DAYS:
        return MINIMUM_WEIGHT_FLOOR

    # Core exponential decay: w(t) = w_0 * 2^(-t / t_half)
    decay_factor = math.pow(2.0, -age_days / half_life)
    effective = base_weight * decay_factor

    # Apply minimum weight floor for numerical stability
    return max(effective, MINIMUM_WEIGHT_FLOOR)


def compute_recency_score(weights: List[float]) -> float:
    """
    Compute the recency score for a collection of temporal weights using
    the harmonic mean.

    The harmonic mean is used rather than the arithmetic mean because temporal
    weights represent rate-like quantities where the effect of any single
    poorly-weighted (old) observation should dominate the aggregate score.
    This penalizes datasets that contain even a few very old transactions,
    which is desirable because stale data can disproportionately degrade
    the quality of downstream aggregations.

    For a set of weights {w_1, w_2, ..., w_n}, the harmonic mean is:
        H = n / (1/w_1 + 1/w_2 + ... + 1/w_n)

    Parameters
    ----------
    weights : List[float]
        Collection of effective weights (post-temporal-adjustment).
        All values must be positive.

    Returns
    -------
    float
        The harmonic mean of the weights, representing the composite
        recency score. Range is (0, max(weights)].

    Raises
    ------
    ValueError
        If weights is empty or contains non-positive values.
    """
    if not weights:
        raise ValueError("Cannot compute recency score from empty weights")

    # Validate all weights are positive (required for harmonic mean)
    for i, w in enumerate(weights):
        if w <= 0:
            raise ValueError(
                f"All weights must be positive for harmonic mean, "
                f"got {w} at index {i}"
            )

    n = len(weights)
    reciprocal_sum = sum(1.0 / w for w in weights)

    # Harmonic mean: n / sum(1/w_i)
    harmonic_mean = n / reciprocal_sum

    return harmonic_mean


def apply_temporal_weights(transactions: List[Dict[str, Any]],
                           reference_date: str,
                           date_field: str = "transaction_date",
                           base_weight_field: str = "base_weight",
                           half_life: float = DEFAULT_HALF_LIFE_DAYS
                           ) -> Tuple[List[Dict[str, Any]], float]:
    """
    Apply temporal weighting to a list of transaction records.

    Each transaction receives an effective weight based on its age relative
    to the reference date, and the collection receives an aggregate recency
    score computed via harmonic mean.

    Parameters
    ----------
    transactions : List[Dict[str, Any]]
        List of transaction records. Each must contain the date_field
        and base_weight_field keys.
    reference_date : str
        The reference date string in ISO format (YYYY-MM-DD) from which
        age is computed.
    date_field : str, optional
        Key in each transaction dict containing the transaction date.
    base_weight_field : str, optional
        Key in each transaction dict containing the base weight value.
    half_life : float, optional
        Half-life parameter for the decay model.

    Returns
    -------
    Tuple[List[Dict[str, Any]], float]
        A tuple of (weighted_transactions, recency_score) where each
        transaction dict is augmented with an 'effective_weight' field.
    """
    from datetime import datetime

    ref_date = datetime.strptime(reference_date, "%Y-%m-%d")
    weighted_transactions = []
    effective_weights = []

    for txn in transactions:
        txn_date = datetime.strptime(txn[date_field], "%Y-%m-%d")
        age_days = (ref_date - txn_date).days

        base_weight = float(txn.get(base_weight_field, 1.0))
        eff_weight = compute_effective_weight(base_weight, age_days, half_life)

        augmented_txn = dict(txn)
        augmented_txn["effective_weight"] = eff_weight
        augmented_txn["age_days"] = age_days
        weighted_transactions.append(augmented_txn)
        effective_weights.append(eff_weight)

    recency_score = compute_recency_score(effective_weights)

    return weighted_transactions, recency_score


def compute_weight_statistics(weights: List[float]) -> Dict[str, float]:
    """
    Compute descriptive statistics for a set of temporal weights.

    Provides summary metrics useful for monitoring the temporal distribution
    of the input dataset and identifying potential staleness issues.

    Parameters
    ----------
    weights : List[float]
        Collection of effective weights.

    Returns
    -------
    Dict[str, float]
        Dictionary containing mean, median, std, min, max, and
        coefficient of variation for the weights.
    """
    if not weights:
        return {
            "mean": 0.0, "median": 0.0, "std": 0.0,
            "min": 0.0, "max": 0.0, "cv": 0.0
        }

    n = len(weights)
    mean_w = sum(weights) / n
    sorted_w = sorted(weights)

    if n % 2 == 0:
        median_w = (sorted_w[n // 2 - 1] + sorted_w[n // 2]) / 2.0
    else:
        median_w = sorted_w[n // 2]

    variance = sum((w - mean_w) ** 2 for w in weights) / n
    std_w = math.sqrt(variance)
    cv = std_w / mean_w if mean_w > 0 else 0.0

    return {
        "mean": mean_w,
        "median": median_w,
        "std": std_w,
        "min": min(weights),
        "max": max(weights),
        "cv": cv
    }
