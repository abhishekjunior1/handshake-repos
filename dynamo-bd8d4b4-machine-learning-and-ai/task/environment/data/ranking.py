"""
Ranking module for model comparison benchmark.

Implements rank-based model comparison using mean rank aggregation
across datasets. Handles ties via fractional (average) ranking and
computes rank-based statistics.

Ranking methodology:
- For each dataset, models are ranked 1..M based on metric performance
- Ties are broken by fractional ranking (average of tied positions)
- Final ranking uses mean rank across all datasets
- Lower mean rank = better model
"""

import math
from typing import Any


def compute_ranks_for_dataset(scores: dict, higher_is_better: bool = True) -> dict:
    """Rank models on a single dataset based on their scores.

    Uses fractional (average) ranking for ties:
    If models A and B tie for rank 2, both get rank 2.5.

    Args:
        scores: dict mapping model_name -> score
        higher_is_better: if True, higher score gets rank 1

    Returns:
        dict mapping model_name -> rank (float, 1-indexed)
    """
    sorted_models = sorted(
        scores.items(),
        key=lambda x: x[1],
        reverse=higher_is_better
    )

    ranks = {}
    i = 0
    while i < len(sorted_models):
        j = i
        while j < len(sorted_models) and sorted_models[j][1] == sorted_models[i][1]:
            j += 1

        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            ranks[sorted_models[k][0]] = avg_rank

        i = j

    return ranks


def compute_mean_ranks(per_dataset_ranks: list) -> dict:
    """Compute mean rank for each model across datasets.

    Args:
        per_dataset_ranks: list of dicts, each mapping model_name -> rank

    Returns:
        dict mapping model_name -> mean_rank
    """
    if not per_dataset_ranks:
        return {}

    models = list(per_dataset_ranks[0].keys())
    mean_ranks = {}

    for model in models:
        total_rank = sum(d[model] for d in per_dataset_ranks)
        mean_ranks[model] = total_rank / len(per_dataset_ranks)

    return mean_ranks


def compute_final_ranking(mean_ranks: dict) -> list:
    """Produce final ordering from mean ranks (lower is better).

    Returns list of (model_name, mean_rank, final_position) tuples
    sorted by mean_rank ascending (best first).
    """
    sorted_models = sorted(mean_ranks.items(), key=lambda x: x[1])
    result = []

    i = 0
    while i < len(sorted_models):
        j = i
        while j < len(sorted_models) and abs(sorted_models[j][1] - sorted_models[i][1]) < 1e-10:
            j += 1

        avg_pos = (i + 1 + j) / 2.0
        for k in range(i, j):
            result.append((sorted_models[k][0], sorted_models[k][1], avg_pos))

        i = j

    return result


def compute_rank_statistics(per_dataset_ranks: list) -> dict:
    """Compute rank statistics for each model.

    Returns dict with per-model statistics:
    - mean_rank: average rank across datasets
    - std_rank: standard deviation of ranks
    - min_rank: best rank achieved
    - max_rank: worst rank achieved
    - rank_range: max_rank - min_rank
    """
    if not per_dataset_ranks:
        return {}

    models = list(per_dataset_ranks[0].keys())
    stats = {}

    for model in models:
        ranks = [d[model] for d in per_dataset_ranks]
        n = len(ranks)
        mean_r = sum(ranks) / n

        if n > 1:
            variance = sum((r - mean_r) ** 2 for r in ranks) / (n - 1)
            std_r = math.sqrt(variance)
        else:
            std_r = 0.0

        stats[model] = {
            "mean_rank": mean_r,
            "std_rank": std_r,
            "min_rank": min(ranks),
            "max_rank": max(ranks),
            "rank_range": max(ranks) - min(ranks)
        }

    return stats


def rank_models_by_score(model_scores: dict, higher_is_better: bool = True) -> list:
    """Rank models by a single score value.

    Args:
        model_scores: dict mapping model -> score
        higher_is_better: if True, highest score gets rank 1

    Returns:
        list of (model, score, rank) tuples, sorted by rank
    """
    sorted_items = sorted(
        model_scores.items(),
        key=lambda x: x[1],
        reverse=higher_is_better
    )

    result = []
    i = 0
    while i < len(sorted_items):
        j = i
        while j < len(sorted_items) and abs(sorted_items[j][1] - sorted_items[i][1]) < 1e-10:
            j += 1

        avg_rank = (i + 1 + j) / 2.0
        for k in range(i, j):
            result.append((sorted_items[k][0], sorted_items[k][1], avg_rank))

        i = j

    return result


def compute_rank_correlation(ranks_a: dict, ranks_b: dict) -> float:
    """Compute Spearman rank correlation between two ranking dicts.

    Args:
        ranks_a: dict mapping model -> rank
        ranks_b: dict mapping model -> rank

    Returns:
        Spearman correlation coefficient in [-1, 1]
    """
    models = sorted(ranks_a.keys())
    n = len(models)

    if n < 2:
        return 1.0

    d_squared_sum = sum(
        (ranks_a[m] - ranks_b[m]) ** 2 for m in models
    )

    rho = 1.0 - (6.0 * d_squared_sum) / (n * (n ** 2 - 1))
    return rho
