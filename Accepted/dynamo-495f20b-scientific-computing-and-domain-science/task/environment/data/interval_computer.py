"""
Credible interval computer for hierarchical Bayesian models.
Computes posterior credible intervals using the t-distribution
to account for uncertainty in variance estimation, which is
particularly important for small-group hierarchical models.
"""

import math


def compute_credible_intervals(shrinkage_results: list, posterior_variances: list,
                               group_estimates: list, credible_level: float) -> list:
    """Compute posterior credible intervals for each group.

    Uses t-distribution quantiles rather than normal approximation.
    For hierarchical models with small groups, the uncertainty in
    variance estimates is non-negligible, and the t-distribution
    provides better coverage than the normal approximation.

    Args:
        shrinkage_results: Shrunken estimates per group.
        posterior_variances: Posterior variance estimates.
        group_estimates: Original group estimates (for df).
        credible_level: Coverage probability (e.g., 0.95).

    Returns:
        List of interval dicts with lower, upper bounds and widths.
    """
    alpha = 1 - credible_level
    intervals = []

    for sr, pv, est in zip(shrinkage_results, posterior_variances, group_estimates):
        n_j = est["n"]
        post_se = pv["posterior_se"]
        shrunken_mean = sr["shrunken_mean"]

        # Degrees of freedom for the t-distribution.
        # For hierarchical models, use (n_j - 1) as the residual df
        # for the within-group variance estimation.
        df = n_j - 1

        # t-quantile for the credible interval
        t_crit = _t_quantile(1 - alpha / 2, df)

        half_width = t_crit * post_se
        lower = shrunken_mean - half_width
        upper = shrunken_mean + half_width

        intervals.append({
            "group_id": sr["group_id"],
            "shrunken_mean": shrunken_mean,
            "lower": lower,
            "upper": upper,
            "width": upper - lower,
            "credible_level": credible_level,
            "df": df,
            "t_critical": t_crit,
            "posterior_se": post_se,
        })

    return intervals


def _t_quantile(p: float, df: int) -> float:
    """Compute the t-distribution quantile using the approximation
    from Abramowitz and Stegun (1964), refined by Hill (1970).

    For large df, converges to normal quantile.
    For small df (< 30), provides accurate t-values.
    """
    if df <= 0:
        return _normal_quantile(p)

    # Normal quantile as starting point
    z = _normal_quantile(p)

    if df >= 1000:
        return z

    # Cornish-Fisher expansion for t-distribution
    g1 = (z ** 3 + z) / (4 * df)
    g2 = (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2)
    g3 = (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / (384 * df ** 3)
    g4 = (79 * z ** 9 + 776 * z ** 7 + 1482 * z ** 5 - 1920 * z ** 3 - 945 * z) / (92160 * df ** 4)

    t = z + g1 + g2 + g3 + g4
    return t


def _normal_quantile(p: float) -> float:
    """Rational approximation to the normal quantile function.
    Accurate to about 4.5e-4 relative error for 0.0002 < p < 0.9998.
    """
    if p <= 0 or p >= 1:
        return 0.0

    if p < 0.5:
        return -_rational_approx(math.sqrt(-2 * math.log(p)))
    else:
        return _rational_approx(math.sqrt(-2 * math.log(1 - p)))


def _rational_approx(t: float) -> float:
    """Rational approximation helper for normal quantile."""
    # Coefficients from Peter Acklam's algorithm
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308
    return t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)



