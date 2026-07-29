"""Correlations module for the EDA pipeline.

Computes bivariate correlations (Pearson and Spearman) between numeric
columns with significance testing. Spearman uses rank-based computation
for robustness against non-linear relationships and outliers.
"""

import math
from typing import List, Dict, Any, Optional, Tuple


def compute_pearson(x: List[Optional[float]],
                    y: List[Optional[float]]) -> Optional[float]:
    """Compute Pearson correlation coefficient.

    Uses pairwise complete observations (excludes pairs where
    either value is None).
    """
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        return None

    x_vals = [p[0] for p in pairs]
    y_vals = [p[1] for p in pairs]

    x_mean = sum(x_vals) / n
    y_mean = sum(y_vals) / n

    numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x_vals, y_vals))
    denom_x = math.sqrt(sum((xi - x_mean) ** 2 for xi in x_vals))
    denom_y = math.sqrt(sum((yi - y_mean) ** 2 for yi in y_vals))

    if denom_x < 1e-15 or denom_y < 1e-15:
        return None

    return numerator / (denom_x * denom_y)


def compute_ranks(values: List[float]) -> List[float]:
    """Compute ranks with average tie-breaking.

    Spearman correlation uses ranks instead of raw values for
    robustness against outliers and non-linear monotonic relationships.
    """
    n = len(values)
    indexed = sorted(range(n), key=lambda i: values[i])

    ranks = [0.0] * n
    i = 0
    while i < n:
        j = i
        while j < n - 1 and values[indexed[j]] == values[indexed[j + 1]]:
            j += 1
        avg_rank = (i + j) / 2.0 + 1.0
        for k in range(i, j + 1):
            ranks[indexed[k]] = avg_rank
        i = j + 1

    return ranks


def compute_spearman(x: List[Optional[float]],
                     y: List[Optional[float]]) -> Optional[float]:
    """Compute Spearman rank correlation coefficient.

    Converts values to ranks then computes Pearson on ranks.
    This provides a measure of monotonic association that is
    robust to outliers and non-linear relationships.
    """
    pairs = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    n = len(pairs)
    if n < 3:
        return None

    x_vals = [p[0] for p in pairs]
    y_vals = [p[1] for p in pairs]

    x_ranks = compute_ranks(x_vals)
    y_ranks = compute_ranks(y_vals)

    # Pearson correlation on ranks
    return compute_pearson(x_ranks, y_ranks)


def compute_p_value(r: float, n: int) -> float:
    """Compute approximate p-value for correlation using t-distribution.

    Uses t = r * sqrt((n-2) / (1-r^2)) with n-2 degrees of freedom.
    Approximates the two-tailed p-value via the normal distribution
    for large n.
    """
    if abs(r) >= 1.0 or n < 4:
        return 0.0

    t_stat = r * math.sqrt((n - 2) / (1 - r * r))
    # Approximate p-value using normal CDF for large t
    df = n - 2
    # Simple approximation: p ≈ 2 * (1 - Phi(|t| * sqrt(df/(df+t^2))))
    z = abs(t_stat) / math.sqrt(1 + t_stat * t_stat / df)
    p = 2.0 * (1.0 - _normal_cdf(z * math.sqrt(df)))
    return min(max(p, 0.0), 1.0)


def _normal_cdf(x: float) -> float:
    """Approximate standard normal CDF."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def compute_correlation_matrix(columns: Dict[str, List[Optional[float]]]
                               ) -> Dict[str, Any]:
    """Compute full correlation matrix for numeric columns.

    Computes both Pearson and Spearman correlations between all
    pairs of numeric columns.

    Args:
        columns: Dict mapping column name to values.

    Returns:
        Dict with 'pearson' and 'spearman' correlation matrices.
    """
    col_names = sorted(columns.keys())
    n_cols = len(col_names)

    pearson_matrix = {}
    spearman_matrix = {}

    for i, col_a in enumerate(col_names):
        pearson_row = {}
        spearman_row = {}
        for j, col_b in enumerate(col_names):
            if i == j:
                pearson_row[col_b] = 1.0
                spearman_row[col_b] = 1.0
            else:
                p_corr = compute_pearson(columns[col_a], columns[col_b])
                s_corr = compute_spearman(columns[col_a], columns[col_b])
                pearson_row[col_b] = round(p_corr, 6) if p_corr is not None else None
                spearman_row[col_b] = round(s_corr, 6) if s_corr is not None else None

        pearson_matrix[col_a] = pearson_row
        spearman_matrix[col_a] = spearman_row

    # Compute pairwise sample sizes
    pairs = [(col_names[i], col_names[j]) for i in range(n_cols) for j in range(i + 1, n_cols)]
    n_valid = sum(1 for a, b in zip(columns[col_names[0]], columns[col_names[0]]) if a is not None) if col_names else 0

    return {
        'pearson': pearson_matrix,
        'spearman': spearman_matrix,
        'columns': col_names,
        'n_pairs': len(pairs)
    }
