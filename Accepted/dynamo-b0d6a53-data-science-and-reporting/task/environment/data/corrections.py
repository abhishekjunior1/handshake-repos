"""
Multiple testing correction methods for experiment analysis.

Implements Bonferroni and Benjamini-Hochberg procedures to control
family-wise error rate (FWER) or false discovery rate (FDR) when
testing multiple hypotheses simultaneously.
"""


def bonferroni_correction(p_values):
    """Apply Bonferroni correction for multiple comparisons.

    Adjusted p_i = p_i * m (capped at 1.0)
    Controls FWER at alpha level.

    Args:
        p_values: List of raw p-values

    Returns:
        List of adjusted p-values
    """
    m = len(p_values)
    if m == 0:
        return []
    return [min(1.0, p * m) for p in p_values]


def benjamini_hochberg(p_values):
    """Apply Benjamini-Hochberg procedure for FDR control.

    Sorts p-values, applies BH adjustment:
    adjusted_p_(i) = min(p_(i) * m / i, 1.0)
    Then enforces monotonicity (step-down).

    Args:
        p_values: List of raw p-values

    Returns:
        List of adjusted p-values (in original order)
    """
    m = len(p_values)
    if m == 0:
        return []

    # Create indexed pairs and sort by p-value
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])

    # Apply BH adjustment
    adjusted = [0.0] * m
    for rank, (orig_idx, p) in enumerate(indexed):
        adj_p = p * m / (rank + 1)
        adjusted[orig_idx] = min(1.0, adj_p)

    # Enforce monotonicity (step-down: ensure adjusted[i] >= adjusted[j] for p_i >= p_j)
    sorted_indices = [idx for idx, _ in indexed]
    for i in range(m - 2, -1, -1):
        idx_current = sorted_indices[i]
        idx_next = sorted_indices[i + 1]
        adjusted[idx_current] = min(adjusted[idx_current], adjusted[idx_next])

    return adjusted


def apply_correction(p_values, method):
    """Apply the specified multiple testing correction.

    Args:
        p_values: List of raw p-values
        method: 'bonferroni' or 'benjamini_hochberg'

    Returns:
        List of corrected p-values
    """
    if method == 'bonferroni':
        return bonferroni_correction(p_values)
    elif method == 'benjamini_hochberg':
        return benjamini_hochberg(p_values)
    else:
        return list(p_values)
