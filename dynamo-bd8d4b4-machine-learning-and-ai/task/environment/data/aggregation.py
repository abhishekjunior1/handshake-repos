"""
Score aggregation module for model comparison benchmark.

Combines normalized per-dataset scores into a single aggregate
score per model. Supports arithmetic and geometric mean aggregation.

Geometric mean is preferred when combining scores from metrics
on different scales because it is scale-invariant: if one dataset's
scores are all multiplied by a constant, the geometric-mean-based
ranking remains unchanged. This property makes it robust to
arbitrary scale differences between datasets.

Arithmetic mean is appropriate when scores have already been
normalized to a common scale and you want equal contribution
from each dataset.
"""

import math
from typing import Any


def arithmetic_mean_aggregate(per_dataset_scores: dict) -> dict:
    """Compute arithmetic mean of scores across datasets.

    Args:
        per_dataset_scores: dict mapping dataset_name -> {model: score}

    Returns:
        dict mapping model_name -> aggregate_score
    """
    if not per_dataset_scores:
        return {}

    datasets = list(per_dataset_scores.keys())
    models = list(per_dataset_scores[datasets[0]].keys())
    n_datasets = len(datasets)

    aggregates = {}
    for model in models:
        total = sum(per_dataset_scores[ds][model] for ds in datasets)
        aggregates[model] = total / n_datasets

    return aggregates


def geometric_mean_aggregate(per_dataset_scores: dict) -> dict:
    """Compute geometric mean of scores across datasets.

    Uses log-space computation for numerical stability:
    geomean = exp(mean(log(scores)))

    Requires all scores to be positive. Scores <= 0 are replaced
    with a small epsilon (1e-10) to avoid log(0).

    The geometric mean is scale-invariant: multiplying all scores
    on one dataset by a constant doesn't change the ranking.
    This makes it robust to different inherent scales across datasets.

    Args:
        per_dataset_scores: dict mapping dataset_name -> {model: score}

    Returns:
        dict mapping model_name -> aggregate_score
    """
    if not per_dataset_scores:
        return {}

    datasets = list(per_dataset_scores.keys())
    models = list(per_dataset_scores[datasets[0]].keys())
    n_datasets = len(datasets)
    epsilon = 1e-10

    aggregates = {}
    for model in models:
        log_sum = 0.0
        for ds in datasets:
            score = per_dataset_scores[ds][model]
            score = max(score, epsilon)
            log_sum += math.log(score)
        aggregates[model] = math.exp(log_sum / n_datasets)

    return aggregates


def aggregate_scores(per_dataset_scores: dict, method: str) -> dict:
    """Aggregate per-dataset scores using the specified method.

    Args:
        per_dataset_scores: dict mapping dataset -> {model: normalized_score}
        method: aggregation method ("arithmetic_mean" or "geometric_mean")

    Returns:
        dict mapping model_name -> aggregate score
    """
    if method == "arithmetic_mean":
        return arithmetic_mean_aggregate(per_dataset_scores)
    elif method == "geometric_mean":
        return geometric_mean_aggregate(per_dataset_scores)
    else:
        raise ValueError(f"Unknown aggregation method: {method}")


def weighted_aggregate(per_dataset_scores: dict, weights: dict) -> dict:
    """Compute weighted aggregate of scores across datasets.

    Args:
        per_dataset_scores: dict mapping dataset -> {model: score}
        weights: dict mapping dataset -> weight

    Returns:
        dict mapping model -> weighted average score
    """
    if not per_dataset_scores:
        return {}

    datasets = list(per_dataset_scores.keys())
    models = list(per_dataset_scores[datasets[0]].keys())

    total_weight = sum(weights.get(ds, 1.0) for ds in datasets)
    if total_weight < 1e-15:
        total_weight = 1.0

    aggregates = {}
    for model in models:
        weighted_sum = sum(
            per_dataset_scores[ds][model] * weights.get(ds, 1.0)
            for ds in datasets
        )
        aggregates[model] = weighted_sum / total_weight

    return aggregates


def compute_score_spread(per_dataset_scores: dict) -> dict:
    """Compute score spread metrics for each model across datasets.

    Returns per-model statistics about how consistent the model
    performs across different datasets.

    Args:
        per_dataset_scores: dict mapping dataset -> {model: score}

    Returns:
        dict mapping model -> {mean, std, min, max, coefficient_of_variation}
    """
    if not per_dataset_scores:
        return {}

    datasets = list(per_dataset_scores.keys())
    models = list(per_dataset_scores[datasets[0]].keys())

    spreads = {}
    for model in models:
        scores = [per_dataset_scores[ds][model] for ds in datasets]
        n = len(scores)
        mean_s = sum(scores) / n

        if n > 1:
            variance = sum((s - mean_s) ** 2 for s in scores) / (n - 1)
            std_s = math.sqrt(variance)
        else:
            std_s = 0.0

        cv = std_s / mean_s if abs(mean_s) > 1e-15 else 0.0

        spreads[model] = {
            "mean": mean_s,
            "std": std_s,
            "min": min(scores),
            "max": max(scores),
            "coefficient_of_variation": cv
        }

    return spreads
