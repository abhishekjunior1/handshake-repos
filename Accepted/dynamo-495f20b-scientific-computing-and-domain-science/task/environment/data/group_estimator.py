"""
Group-level parameter estimator for hierarchical models.
Computes sufficient statistics (means, variances) for each group
and overall pooled estimates needed for empirical Bayes shrinkage.
"""

import math


def compute_group_estimates(groups: list) -> list:
    """Compute parameter estimates for each group.

    Returns list of dicts with group means, variances, and standard errors.
    """
    estimates = []
    for group in groups:
        obs = group["observations"]
        n = group["n"]
        mean = sum(obs) / n
        # Sample variance with Bessel's correction
        ss = sum((x - mean) ** 2 for x in obs)
        variance = ss / (n - 1)
        se = math.sqrt(variance / n)

        estimates.append({
            "group_id": group["id"],
            "mean": mean,
            "variance": variance,
            "se": se,
            "n": n,
            "sum_sq_dev": ss,
        })
    return estimates


def compute_pooled_variance(group_estimates: list) -> float:
    """Compute pooled within-group variance (sigma²_w).

    Uses the weighted average of group variances, weighted by degrees of freedom.
    This is the standard pooled variance estimator for balanced/unbalanced designs.
    """
    numerator = 0.0
    denominator = 0.0
    for est in group_estimates:
        df = est["n"] - 1
        numerator += df * est["variance"]
        denominator += df
    if denominator == 0:
        return 0.0
    return numerator / denominator


def compute_between_group_variance(group_estimates: list, pooled_var: float) -> float:
    """Compute between-group variance (tau²) using method of moments.

    tau² = max(0, MSB/n_bar - sigma²_w/n_bar)
    where MSB is the mean square between groups.
    This is the DerSimonian-Laird-style estimator for hierarchical models.
    """
    k = len(group_estimates)
    if k < 2:
        return 0.0

    # Compute grand mean of group means (unweighted)
    grand_mean = sum(est["mean"] for est in group_estimates) / k

    # Mean square between groups
    msb = sum((est["mean"] - grand_mean) ** 2 for est in group_estimates) / (k - 1)

    # Harmonic mean of group sizes for unbalanced designs
    n_harmonic = k / sum(1.0 / est["n"] for est in group_estimates)

    # Method of moments estimate of tau²
    tau_sq = msb - pooled_var / n_harmonic
    return max(0.0, tau_sq)

