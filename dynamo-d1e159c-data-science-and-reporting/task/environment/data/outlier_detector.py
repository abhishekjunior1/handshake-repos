"""Outlier Detection module for the EDA pipeline.

Detects outliers using IQR (Tukey's fences) and z-score methods.
Both methods require clean numeric data without missing values for
accurate threshold computation.
"""

import math
from typing import List, Dict, Any, Optional, Tuple


def compute_iqr_bounds(values: List[Optional[float]],
                       multiplier: float = 1.5
                       ) -> Tuple[float, float]:
    """Compute IQR-based outlier bounds (Tukey's fences).

    Lower bound = Q1 - multiplier * IQR
    Upper bound = Q3 + multiplier * IQR

    Args:
        values: Numeric values (None values excluded).
        multiplier: IQR multiplier (default 1.5).

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    valid = sorted(v for v in values if v is not None)
    n = len(valid)
    if n < 4:
        return (float('-inf'), float('inf'))

    # Q1 and Q3 via linear interpolation
    q1_idx = 0.25 * (n - 1)
    q3_idx = 0.75 * (n - 1)

    q1_lower = int(math.floor(q1_idx))
    q1_frac = q1_idx - q1_lower
    q1 = valid[q1_lower] * (1 - q1_frac) + valid[min(q1_lower + 1, n - 1)] * q1_frac

    q3_lower = int(math.floor(q3_idx))
    q3_frac = q3_idx - q3_lower
    q3 = valid[q3_lower] * (1 - q3_frac) + valid[min(q3_lower + 1, n - 1)] * q3_frac

    iqr = q3 - q1
    lower = q1 - multiplier * iqr
    upper = q3 + multiplier * iqr

    return (lower, upper)


def detect_outliers_iqr(values: List[Optional[float]],
                        multiplier: float = 1.5) -> Dict[str, Any]:
    """Detect outliers using the IQR method.

    Args:
        values: Numeric values to check.
        multiplier: IQR multiplier for fence computation.

    Returns:
        Dict with bounds, outlier indices, and outlier values.
    """
    lower, upper = compute_iqr_bounds(values, multiplier)

    outlier_indices = []
    outlier_values = []
    for i, v in enumerate(values):
        if v is not None and (v < lower or v > upper):
            outlier_indices.append(i)
            outlier_values.append(v)

    return {
        'method': 'iqr',
        'lower_bound': round(lower, 6),
        'upper_bound': round(upper, 6),
        'n_outliers': len(outlier_indices),
        'outlier_indices': outlier_indices,
        'outlier_values': [round(v, 6) for v in outlier_values]
    }


def detect_outliers_zscore(values: List[Optional[float]],
                           threshold: float = 3.0) -> Dict[str, Any]:
    """Detect outliers using the z-score method.

    Args:
        values: Numeric values to check.
        threshold: Z-score threshold (default 3.0).

    Returns:
        Dict with threshold, outlier indices, and outlier values.
    """
    valid = [v for v in values if v is not None]
    n = len(valid)
    if n < 2:
        return {'method': 'zscore', 'n_outliers': 0, 'outlier_indices': [], 'outlier_values': []}

    mean = sum(valid) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in valid) / (n - 1))
    if std < 1e-15:
        return {'method': 'zscore', 'n_outliers': 0, 'outlier_indices': [], 'outlier_values': []}

    outlier_indices = []
    outlier_values = []
    for i, v in enumerate(values):
        if v is not None:
            z = abs(v - mean) / std
            if z > threshold:
                outlier_indices.append(i)
                outlier_values.append(v)

    return {
        'method': 'zscore',
        'threshold': threshold,
        'mean': round(mean, 6),
        'std': round(std, 6),
        'n_outliers': len(outlier_indices),
        'outlier_indices': outlier_indices,
        'outlier_values': [round(v, 6) for v in outlier_values]
    }


def clean_outliers(values: List[Optional[float]],
                   outlier_indices: List[int]) -> List[Optional[float]]:
    """Replace outlier values with None (mark as missing).

    Args:
        values: Original values.
        outlier_indices: Indices to replace with None.

    Returns:
        Cleaned values list.
    """
    cleaned = values[:]
    for idx in outlier_indices:
        cleaned[idx] = None
    return cleaned
