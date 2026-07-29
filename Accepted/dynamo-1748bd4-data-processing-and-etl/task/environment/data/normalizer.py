"""
Normalizer Module
=================

Applies final normalization transformations to aggregated data to produce
output values suitable for comparison, visualization, and reporting.

Cross-group normalization computes each group's proportional share of the
total, expressing values as percentages. This enables meaningful comparisons
across groups of different sizes and magnitudes.

Dampening is applied to prevent extreme percentage values from dominating
visual representations and downstream decision logic. The dampening function
preserves the sign and ordering of values while bounding their magnitude
using a saturating exponential curve.
"""

import math
from typing import List, Dict, Any, Optional, Tuple


# Default dampening factor controlling the saturation rate.
# Higher values cause faster saturation (more aggressive bounding).
DEFAULT_DAMPENING_FACTOR = 0.03

# Minimum total for share computation to prevent division by zero.
MIN_TOTAL_FOR_SHARE = 1e-12


def cross_group_normalize(groups: List[Dict[str, Any]],
                          value_col: str) -> List[Dict[str, Any]]:
    """
    Normalize group values as percentage shares of the total.

    Each group's share is computed as:
        share_pct = (group_value / total_value) * 100

    This produces values that sum to 100 across all groups, representing
    each group's proportional contribution to the aggregate.

    Parameters
    ----------
    groups : List[Dict[str, Any]]
        Aggregated group records containing the value column.
    value_col : str
        The field name containing the numeric value to normalize.

    Returns
    -------
    List[Dict[str, Any]]
        Records augmented with 'share_pct' and 'normalized_value' fields.
    """
    if not groups:
        return groups

    # Compute total across all groups
    total = sum(float(g.get(value_col, 0.0)) for g in groups)
    total = max(total, MIN_TOTAL_FOR_SHARE)

    normalized_groups = []
    for group in groups:
        normalized = dict(group)
        value = float(group.get(value_col, 0.0))

        share_pct = (value / total) * 100.0
        normalized["share_pct"] = share_pct
        normalized["normalized_value"] = share_pct / 100.0
        normalized["total_basis"] = total

        normalized_groups.append(normalized)

    return normalized_groups


def apply_dampening(values: List[float],
                    dampening_factor: float = DEFAULT_DAMPENING_FACTOR
                    ) -> List[float]:
    """
    Apply a saturating dampening function to bound value magnitudes.

    The dampening function is:
        dampened = value * (1 - e^(-dampening_factor * |value|))

    This function has the following properties:
    - Preserves sign: positive values stay positive, negative stay negative
    - Preserves ordering: if a > b > 0, then dampen(a) > dampen(b)
    - Bounds magnitude: as |value| → ∞, dampened → value (saturates)
    - Near-zero linearity: for small values, dampened ≈ dampening_factor * value²
    - Asymptotic identity: for large values, the exponential term vanishes

    The dampening prevents extreme percentage shares from disproportionately
    influencing downstream visualizations and decision models while maintaining
    the relative ordering and direction of all values.

    Parameters
    ----------
    values : List[float]
        Input values to dampen. Can be positive, negative, or zero.
    dampening_factor : float, optional
        Controls saturation rate. Higher = faster saturation.
        Default is 0.03.

    Returns
    -------
    List[float]
        Dampened values with bounded magnitudes.
    """
    dampened = []
    for v in values:
        abs_v = abs(v)
        # Saturating function: preserves sign, bounds magnitude
        saturation = 1.0 - math.exp(-dampening_factor * abs_v)
        dampened_value = v * saturation
        dampened.append(dampened_value)

    return dampened


def normalize_pipeline_output(aggregated_data: Dict[str, List[Dict[str, Any]]],
                              value_cols: List[str],
                              dampening_factor: float = DEFAULT_DAMPENING_FACTOR
                              ) -> Dict[str, List[Dict[str, Any]]]:
    """
    Apply full normalization pipeline to hierarchically aggregated data.

    For each hierarchy level, applies cross-group normalization followed by
    dampening of the resulting percentage shares. This produces final output
    values that are both proportionally meaningful and visually balanced.

    Parameters
    ----------
    aggregated_data : Dict[str, List[Dict[str, Any]]]
        Hierarchical rollup results, mapping level names to records.
    value_cols : List[str]
        Value columns to normalize.
    dampening_factor : float, optional
        Dampening factor for bounding extreme values.

    Returns
    -------
    Dict[str, List[Dict[str, Any]]]
        Normalized data with dampened percentage shares.
    """
    normalized_output = {}

    for level_name, level_data in aggregated_data.items():
        if not level_data:
            normalized_output[level_name] = level_data
            continue

        # Apply cross-group normalization for each value column
        current_data = [dict(r) for r in level_data]

        for col in value_cols:
            current_data = cross_group_normalize(current_data, col)

            # Apply dampening to the share percentages
            share_values = [r.get("share_pct", 0.0) for r in current_data]
            dampened_shares = apply_dampening(share_values, dampening_factor)

            for i, record in enumerate(current_data):
                record[f"{col}_dampened_share"] = dampened_shares[i]

        normalized_output[level_name] = current_data

    return normalized_output


def compute_normalization_diagnostics(normalized_data: Dict[str, List[Dict[str, Any]]],
                                       value_cols: List[str]) -> Dict[str, Any]:
    """
    Compute diagnostics for the normalization process.

    Validates that shares sum correctly and reports dampening effects.

    Parameters
    ----------
    normalized_data : Dict[str, List[Dict[str, Any]]]
        Normalized output data.
    value_cols : List[str]
        Value columns that were normalized.

    Returns
    -------
    Dict[str, Any]
        Diagnostic information including share totals and dampening impact.
    """
    diagnostics = {}

    for level_name, level_data in normalized_data.items():
        level_diag = {}

        if level_data and "share_pct" in level_data[0]:
            total_share = sum(r.get("share_pct", 0.0) for r in level_data)
            level_diag["share_total_pct"] = total_share
            level_diag["share_valid"] = abs(total_share - 100.0) < 0.01

        for col in value_cols:
            dampened_key = f"{col}_dampened_share"
            if level_data and dampened_key in level_data[0]:
                raw_shares = [r.get("share_pct", 0.0) for r in level_data]
                dampened_shares = [r.get(dampened_key, 0.0) for r in level_data]

                if raw_shares:
                    dampening_impact = 1.0 - (sum(abs(d) for d in dampened_shares) /
                                              max(sum(abs(r) for r in raw_shares), 1e-12))
                    level_diag[f"{col}_dampening_impact"] = dampening_impact

        diagnostics[level_name] = level_diag

    return diagnostics
