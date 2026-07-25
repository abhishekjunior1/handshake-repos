"""Multiple testing correction procedures for A/B experiments.

Implements Bonferroni correction and Benjamini-Hochberg (BH) procedure
for controlling family-wise error rate and false discovery rate respectively.
"""

from typing import Any


def apply_bonferroni(
    p_values: list[float],
    alpha: float,
    num_comparisons: int
) -> dict[str, Any]:
    """Apply Bonferroni correction for multiple comparisons.
    
    Adjusts the significance threshold by dividing by the number of
    comparisons. Each adjusted p-value is min(p * m, 1.0).
    
    Parameters
    ----------
    p_values : list of raw p-values to correct
    alpha : original significance level
    num_comparisons : total number of hypothesis tests (m)
    
    Returns dict with adjusted_p_values, adjusted_alpha, and rejection decisions.
    """
    adjusted_alpha = alpha / num_comparisons
    adjusted_p_values = [min(p * num_comparisons, 1.0) for p in p_values]
    rejections = [bool(p < adjusted_alpha) for p in p_values]
    
    return {
        "method": "bonferroni",
        "adjusted_p_values": [round(p, 10) for p in adjusted_p_values],
        "adjusted_alpha": adjusted_alpha,
        "rejections": rejections,
        "num_comparisons": num_comparisons
    }


def apply_benjamini_hochberg(
    p_values: list[float],
    alpha: float,
    num_comparisons: int
) -> dict[str, Any]:
    """Apply Benjamini-Hochberg procedure for FDR control.
    
    Steps:
    1. Sort p-values in ascending order
    2. For rank i (1-indexed), compute adjusted threshold: i/m * alpha
    3. Find largest k where p_(k) <= k/m * alpha
    4. Reject all hypotheses with rank <= k
    
    Adjusted p-values use step-up enforcement of monotonicity.
    
    Parameters
    ----------
    p_values : list of raw p-values to correct
    alpha : target FDR level
    num_comparisons : total number of tests (m)
    """
    m = num_comparisons
    n = len(p_values)
    
    if n == 0:
        return {
            "method": "benjamini_hochberg",
            "adjusted_p_values": [],
            "rejections": [],
            "num_comparisons": m
        }
    
    # Create indexed pairs and sort by p-value
    indexed = sorted(enumerate(p_values), key=lambda x: x[1])
    
    # Compute adjusted p-values with step-up monotonicity enforcement
    adjusted = [0.0] * n
    
    # Start from largest rank and work backwards to enforce monotonicity
    for rank_idx in range(n - 1, -1, -1):
        orig_idx, p = indexed[rank_idx]
        rank = rank_idx + 1  # 1-indexed rank
        
        # Raw adjustment: p * m / rank
        raw_adjusted = p * m / rank
        
        if rank_idx == n - 1:
            adjusted[orig_idx] = min(raw_adjusted, 1.0)
        else:
            # Enforce monotonicity: adjusted p-value can't exceed the next larger one
            next_orig_idx = indexed[rank_idx + 1][0]
            adjusted[orig_idx] = min(raw_adjusted, adjusted[next_orig_idx], 1.0)
    
    rejections = [bool(adj_p <= alpha) for adj_p in adjusted]
    
    return {
        "method": "benjamini_hochberg",
        "adjusted_p_values": [round(p, 10) for p in adjusted],
        "rejections": rejections,
        "num_comparisons": m
    }


def get_correction_function(method: str):
    """Return the appropriate correction function by name."""
    methods = {
        "bonferroni": apply_bonferroni,
        "benjamini_hochberg": apply_benjamini_hochberg
    }
    if method not in methods:
        raise ValueError(f"Unknown correction method: {method}. Use one of: {list(methods.keys())}")
    return methods[method]
