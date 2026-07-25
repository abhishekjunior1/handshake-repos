"""
Contribution Scoring Module
============================

Computes contribution scores for individual entities within their respective
groups. The contribution score quantifies each entity's weighted share of the
total group value, providing a normalized measure of relative importance.

The core formula is:
    contribution(entity) = (value * weight) / group_total_weighted_value

where group_total_weighted_value = sum(value_i * weight_i) for all entities
in the same group.

Normalization methods are provided to rescale contribution scores into
standardized ranges for downstream comparison and visualization.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


# Epsilon for numerical comparisons and division safety
EPSILON = 1e-12

# Supported normalization methods
VALID_NORMALIZATION_METHODS = ('min_max', 'z_score')


def weighted_contribution(value: float, weight: float,
                          group_total_weighted_value: float) -> float:
    """
    Compute the weighted contribution of a single entity within its group.

    The contribution score represents what fraction of the group's total
    weighted value is attributable to this entity. Scores sum to 1.0
    within each group when all entities are included.

    Parameters
    ----------
    value : float
        The raw metric value for this entity (e.g., revenue, quantity).
    weight : float
        The effective weight for this entity (e.g., temporal weight).
    group_total_weighted_value : float
        The sum of (value * weight) for all entities in the same group.
        Must be positive.

    Returns
    -------
    float
        The contribution score in range [0, 1]. Returns 0 if
        group_total_weighted_value is effectively zero.

    Examples
    --------
    >>> weighted_contribution(100, 1.0, 500)
    0.2
    >>> weighted_contribution(200, 0.5, 500)
    0.2
    """
    if abs(group_total_weighted_value) < EPSILON:
        return 0.0

    contribution = (value * weight) / group_total_weighted_value
    return contribution


def compute_group_totals(records: List[Dict[str, Any]],
                         group_key: str,
                         value_field: str,
                         weight_field: str = "effective_weight"
                         ) -> Dict[str, float]:
    """
    Compute the total weighted value for each group.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        List of records containing group, value, and weight fields.
    group_key : str
        The field name identifying group membership.
    value_field : str
        The field name containing the metric value.
    weight_field : str, optional
        The field name containing the weight. Default is 'effective_weight'.

    Returns
    -------
    Dict[str, float]
        Mapping from group identifier to total weighted value.
    """
    group_totals = defaultdict(float)

    for record in records:
        group = record[group_key]
        value = float(record[value_field])
        weight = float(record.get(weight_field, 1.0))
        group_totals[group] += value * weight

    return dict(group_totals)


def score_contributions(records: List[Dict[str, Any]],
                        group_key: str,
                        value_field: str,
                        weight_field: str = "effective_weight"
                        ) -> List[Dict[str, Any]]:
    """
    Compute contribution scores for all records within their groups.

    Each record is augmented with a 'contribution_score' field representing
    its weighted share of the group total.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        Input records with group, value, and weight information.
    group_key : str
        Field identifying group membership.
    value_field : str
        Field containing the metric value.
    weight_field : str, optional
        Field containing the weight.

    Returns
    -------
    List[Dict[str, Any]]
        Records augmented with 'contribution_score' field.
    """
    group_totals = compute_group_totals(records, group_key, value_field, weight_field)

    scored_records = []
    for record in records:
        scored = dict(record)
        group = record[group_key]
        value = float(record[value_field])
        weight = float(record.get(weight_field, 1.0))
        total = group_totals.get(group, 0.0)

        scored["contribution_score"] = weighted_contribution(value, weight, total)
        scored["group_total_weighted_value"] = total
        scored_records.append(scored)

    return scored_records


def normalize_scores(scores: List[Dict[str, Any]],
                     method: str = 'min_max',
                     score_field: str = 'contribution_score',
                     group_key: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Normalize contribution scores using the specified method.

    Supports min-max scaling and z-score standardization. Normalization
    is applied to produce comparable score distributions.

    Global normalization range ensures cross-group comparability on a
    unified scale. This prevents artificial inflation of scores in groups
    with narrow value ranges and ensures that a normalized score of 0.5
    means the same thing regardless of which group it belongs to.

    Parameters
    ----------
    scores : List[Dict[str, Any]]
        Records containing contribution scores to normalize.
    method : str, optional
        Normalization method: 'min_max' or 'z_score'. Default is 'min_max'.
    score_field : str, optional
        Field containing the score to normalize. Default is 'contribution_score'.
    group_key : Optional[str], optional
        Field identifying group membership. Used for grouped statistics.

    Returns
    -------
    List[Dict[str, Any]]
        Records with added 'normalized_score' field.

    Raises
    ------
    ValueError
        If an unsupported normalization method is specified.
    """
    if method not in VALID_NORMALIZATION_METHODS:
        raise ValueError(
            f"Unsupported normalization method '{method}'. "
            f"Valid options: {VALID_NORMALIZATION_METHODS}"
        )

    if not scores:
        return scores

    normalized = [dict(s) for s in scores]

    if method == 'min_max':
        # Global normalization range ensures cross-group comparability
        # on a unified scale. This approach uses the global minimum and
        # maximum across all groups to establish the normalization bounds,
        # ensuring consistent interpretation of normalized values regardless
        # of group membership.
        all_values = [float(s[score_field]) for s in scores]
        global_min = min(all_values)
        global_max = max(all_values)
        value_range = global_max - global_min

        for record in normalized:
            raw_score = float(record[score_field])
            if abs(value_range) < EPSILON:
                record["normalized_score"] = 0.5
            else:
                record["normalized_score"] = (raw_score - global_min) / value_range

    elif method == 'z_score':
        all_values = [float(s[score_field]) for s in scores]
        n = len(all_values)
        mean_val = sum(all_values) / n
        variance = sum((v - mean_val) ** 2 for v in all_values) / n
        std_val = math.sqrt(variance) if variance > 0 else 1.0

        for record in normalized:
            raw_score = float(record[score_field])
            if abs(std_val) < EPSILON:
                record["normalized_score"] = 0.0
            else:
                record["normalized_score"] = (raw_score - mean_val) / std_val

    return normalized


def compute_contribution_statistics(scores: List[Dict[str, Any]],
                                    score_field: str = "contribution_score"
                                    ) -> Dict[str, Any]:
    """
    Compute summary statistics for contribution scores.

    Parameters
    ----------
    scores : List[Dict[str, Any]]
        Records with contribution scores.
    score_field : str, optional
        Field containing the score values.

    Returns
    -------
    Dict[str, Any]
        Statistical summary including concentration metrics.
    """
    values = [float(s[score_field]) for s in scores]
    if not values:
        return {"count": 0, "mean": 0.0, "gini": 0.0}

    n = len(values)
    mean_val = sum(values) / n
    sorted_vals = sorted(values)

    # Compute Gini coefficient for concentration measurement
    cumulative = 0.0
    weighted_sum = 0.0
    for i, v in enumerate(sorted_vals):
        cumulative += v
        weighted_sum += (2 * (i + 1) - n - 1) * v

    gini = weighted_sum / (n * sum(values)) if sum(values) > 0 else 0.0

    return {
        "count": n,
        "mean": mean_val,
        "max": max(values),
        "min": min(values),
        "gini_coefficient": abs(gini),
        "top_concentration": sorted_vals[-1] / sum(values) if sum(values) > 0 else 0.0
    }
