"""
Score normalization module for model comparison benchmark.

Normalizes raw performance scores to a common scale before
aggregation. Supports min-max normalization and z-score
standardization, applied per-dataset to ensure comparability
across datasets with different score ranges.

Per-dataset normalization is critical when datasets produce
metrics on fundamentally different scales (e.g., accuracy on
a 2-class problem vs a 50-class problem). Without per-dataset
normalization, datasets with naturally larger score spreads
would dominate the aggregate.
"""

import math
from typing import Any


def min_max_normalize(scores: dict, dataset_scores: dict = None) -> dict:
    """Apply min-max normalization to map scores to [0, 1].

    For per-dataset normalization, the min and max are computed
    from all model scores ON THAT DATASET. This ensures each
    dataset contributes equally regardless of its inherent scale.

    Formula: normalized = (score - min) / (max - min)
    If max == min, all normalized scores are 0.5.

    Args:
        scores: dict mapping model_name -> raw score
        dataset_scores: optional dict of all scores for computing
                       min/max range. If None, uses scores dict.

    Returns:
        dict mapping model_name -> normalized score in [0, 1]
    """
    reference = dataset_scores if dataset_scores is not None else scores

    all_values = list(reference.values())
    if not all_values:
        return {}

    min_val = min(all_values)
    max_val = max(all_values)

    if abs(max_val - min_val) < 1e-15:
        return {model: 0.5 for model in scores}

    normalized = {}
    for model, score in scores.items():
        normalized[model] = (score - min_val) / (max_val - min_val)

    return normalized


def z_score_normalize(scores: dict, dataset_scores: dict = None) -> dict:
    """Apply z-score standardization to scores.

    Transforms scores to have mean=0 and std=1 based on the
    reference distribution from the dataset.

    Formula: z = (score - mean) / std
    If std == 0, all z-scores are 0.

    Args:
        scores: dict mapping model_name -> raw score
        dataset_scores: optional dict of all scores for computing
                       mean/std. If None, uses scores dict.

    Returns:
        dict mapping model_name -> z-score
    """
    reference = dataset_scores if dataset_scores is not None else scores

    all_values = list(reference.values())
    if not all_values:
        return {}

    n = len(all_values)
    mean = sum(all_values) / n

    if n > 1:
        variance = sum((v - mean) ** 2 for v in all_values) / (n - 1)
        std = math.sqrt(variance)
    else:
        std = 0.0

    if std < 1e-15:
        return {model: 0.0 for model in scores}

    normalized = {}
    for model, score in scores.items():
        normalized[model] = (score - mean) / std

    return normalized


def normalize_scores(scores: dict, method: str, dataset_scores: dict = None) -> dict:
    """Normalize scores using the specified method.

    Args:
        scores: dict mapping model_name -> raw score
        method: normalization method ("min_max", "z_score", or "none")
        dataset_scores: reference scores for computing normalization params

    Returns:
        dict mapping model_name -> normalized score
    """
    if method == "min_max":
        return min_max_normalize(scores, dataset_scores)
    elif method == "z_score":
        return z_score_normalize(scores, dataset_scores)
    elif method == "none":
        return dict(scores)
    else:
        raise ValueError(f"Unknown normalization method: {method}")


def compute_normalization_params(all_scores: dict) -> dict:
    """Compute normalization parameters from a set of scores.

    Returns the statistics needed for normalization:
    min, max, mean, std, count.

    Args:
        all_scores: dict mapping model_name -> score

    Returns:
        dict with keys: min, max, mean, std, count
    """
    values = list(all_scores.values())
    if not values:
        return {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0, "count": 0}

    n = len(values)
    min_val = min(values)
    max_val = max(values)
    mean_val = sum(values) / n

    if n > 1:
        variance = sum((v - mean_val) ** 2 for v in values) / (n - 1)
        std_val = math.sqrt(variance)
    else:
        std_val = 0.0

    return {
        "min": min_val,
        "max": max_val,
        "mean": mean_val,
        "std": std_val,
        "count": n
    }


def rescale_to_range(scores: dict, target_min: float = 0.0,
                     target_max: float = 1.0) -> dict:
    """Rescale normalized scores to an arbitrary target range.

    Args:
        scores: dict mapping model_name -> score (assumed already normalized)
        target_min: desired minimum value
        target_max: desired maximum value

    Returns:
        dict mapping model_name -> rescaled score
    """
    values = list(scores.values())
    if not values:
        return {}

    curr_min = min(values)
    curr_max = max(values)

    if abs(curr_max - curr_min) < 1e-15:
        mid = (target_min + target_max) / 2.0
        return {model: mid for model in scores}

    rescaled = {}
    for model, score in scores.items():
        fraction = (score - curr_min) / (curr_max - curr_min)
        rescaled[model] = target_min + fraction * (target_max - target_min)

    return rescaled
