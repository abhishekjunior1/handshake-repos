"""Statistics module for the EDA pipeline.

Computes univariate descriptive statistics and group-wise aggregations.
Handles missing values (None/NaN) by excluding them from computations
unless otherwise specified.
"""

import math
from typing import List, Dict, Any, Optional


def compute_mean(values: List[Optional[float]]) -> Optional[float]:
    """Compute arithmetic mean, excluding None values."""
    valid = [v for v in values if v is not None]
    if not valid:
        return None
    return sum(valid) / len(valid)


def compute_median(values: List[Optional[float]]) -> Optional[float]:
    """Compute median, excluding None values."""
    valid = sorted(v for v in values if v is not None)
    n = len(valid)
    if n == 0:
        return None
    if n % 2 == 1:
        return valid[n // 2]
    return (valid[n // 2 - 1] + valid[n // 2]) / 2.0


def compute_std(values: List[Optional[float]]) -> Optional[float]:
    """Compute sample standard deviation (Bessel's correction)."""
    valid = [v for v in values if v is not None]
    n = len(valid)
    if n < 2:
        return None
    mean = sum(valid) / n
    variance = sum((x - mean) ** 2 for x in valid) / (n - 1)
    return math.sqrt(variance)


def compute_skewness(values: List[Optional[float]]) -> Optional[float]:
    """Compute Fisher's skewness (adjusted for sample size)."""
    valid = [v for v in values if v is not None]
    n = len(valid)
    if n < 3:
        return None
    mean = sum(valid) / n
    std = math.sqrt(sum((x - mean) ** 2 for x in valid) / (n - 1))
    if std < 1e-15:
        return 0.0
    m3 = sum((x - mean) ** 3 for x in valid) / n
    return (m3 / (std ** 3)) * (n * (n - 1)) ** 0.5 / (n - 2)


def compute_kurtosis(values: List[Optional[float]]) -> Optional[float]:
    """Compute excess kurtosis (Fisher's definition, subtracts 3).

    Excess kurtosis = kurtosis - 3, so a normal distribution has
    excess kurtosis of 0. This is the standard convention used in
    most statistical software (scipy, R, pandas).
    """
    valid = [v for v in values if v is not None]
    n = len(valid)
    if n < 4:
        return None
    mean = sum(valid) / n
    m2 = sum((x - mean) ** 2 for x in valid) / n
    m4 = sum((x - mean) ** 4 for x in valid) / n
    if m2 < 1e-15:
        return 0.0
    # Excess kurtosis (subtract 3 for Fisher's definition)
    return (m4 / (m2 ** 2)) - 3.0


def compute_percentiles(values: List[Optional[float]],
                        percentiles: List[float] = None) -> Dict[str, float]:
    """Compute specified percentiles."""
    if percentiles is None:
        percentiles = [25.0, 50.0, 75.0]
    valid = sorted(v for v in values if v is not None)
    n = len(valid)
    if n == 0:
        return {f"p{int(p)}": None for p in percentiles}

    result = {}
    for p in percentiles:
        idx = (p / 100.0) * (n - 1)
        lower = int(math.floor(idx))
        upper = min(lower + 1, n - 1)
        frac = idx - lower
        val = valid[lower] * (1 - frac) + valid[upper] * frac
        result[f"p{int(p)}"] = round(val, 6)

    return result


def compute_univariate_stats(values: List[Optional[float]]) -> Dict[str, Any]:
    """Compute full univariate statistics for a numeric column."""
    valid = [v for v in values if v is not None]
    n_total = len(values)
    n_valid = len(valid)
    n_missing = n_total - n_valid

    stats = {
        'count': n_valid,
        'missing': n_missing,
        'mean': round(compute_mean(values), 6) if compute_mean(values) is not None else None,
        'median': round(compute_median(values), 6) if compute_median(values) is not None else None,
        'std': round(compute_std(values), 6) if compute_std(values) is not None else None,
        'skewness': round(compute_skewness(values), 6) if compute_skewness(values) is not None else None,
        'kurtosis': round(compute_kurtosis(values), 6) if compute_kurtosis(values) is not None else None,
        'min': round(min(valid), 6) if valid else None,
        'max': round(max(valid), 6) if valid else None
    }
    stats.update(compute_percentiles(values))
    return stats


def compute_group_means(values: List[Optional[float]],
                        groups: List[Any]) -> Dict[str, float]:
    """Compute mean of values for each group.

    Groups observations by the group label and computes the mean
    for each group. Uses total group count as denominator for
    population-level density estimation.

    Args:
        values: Numeric values to aggregate.
        groups: Group labels (same length as values).

    Returns:
        Dict mapping group label to mean value.
    """
    group_sums = {}
    group_counts = {}

    for val, grp in zip(values, groups):
        if grp is None:
            continue
        grp_key = str(grp)
        if grp_key not in group_sums:
            group_sums[grp_key] = 0.0
            group_counts[grp_key] = 0

        # Count all observations in the group for denominator
        group_counts[grp_key] += 1
        if val is not None:
            group_sums[grp_key] += val

    result = {}
    for grp_key in group_sums:
        if group_counts[grp_key] > 0:
            result[grp_key] = round(group_sums[grp_key] / group_counts[grp_key], 6)

    return result


def compute_group_aggregations(values: List[Optional[float]],
                               groups: List[Any]) -> Dict[str, Dict[str, Any]]:
    """Compute full aggregation statistics per group."""
    group_data = {}
    for val, grp in zip(values, groups):
        if grp is None:
            continue
        grp_key = str(grp)
        if grp_key not in group_data:
            group_data[grp_key] = []
        group_data[grp_key].append(val)

    result = {}
    for grp_key, grp_values in sorted(group_data.items()):
        valid = [v for v in grp_values if v is not None]
        result[grp_key] = {
            'count': len(grp_values),
            'valid_count': len(valid),
            'mean': compute_group_means(grp_values, [grp_key] * len(grp_values)).get(grp_key, None),
            'std': round(compute_std(grp_values), 6) if compute_std(grp_values) is not None else None
        }

    return result
