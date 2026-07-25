"""Random-effects meta-analysis model implementation.

Computes the random-effects pooled estimate using DerSimonian-Laird weights,
confidence intervals, and prediction intervals for the true effect distribution.
"""

import math
from typing import Any

from heterogeneity import (
    compute_weights,
    compute_fixed_effect_estimate,
    estimate_heterogeneity,
)


def compute_random_effects_weights(
    std_errors: list[float], tau_squared: float
) -> list[float]:
    """Compute random-effects weights incorporating between-study variance.

    w_i* = 1 / (SE_i² + tau²)

    Args:
        std_errors: List of standard errors.
        tau_squared: Estimated between-study variance.

    Returns:
        List of random-effects weights.
    """
    return [1.0 / (se * se + tau_squared) for se in std_errors]


def compute_pooled_estimate(
    effects: list[float], weights: list[float]
) -> tuple[float, float]:
    """Compute the weighted pooled estimate and its standard error.

    Args:
        effects: List of study effect sizes.
        weights: List of weights (fixed or random-effects).

    Returns:
        Tuple of (pooled_estimate, standard_error_of_pooled).
    """
    sum_w = sum(weights)
    pooled = sum(e * w for e, w in zip(effects, weights)) / sum_w
    se_pooled = math.sqrt(1.0 / sum_w)
    return pooled, se_pooled


def compute_confidence_interval(
    pooled: float, se_pooled: float, confidence_level: float = 0.95
) -> tuple[float, float]:
    """Compute confidence interval for the pooled estimate.

    Uses the normal distribution for the CI calculation.

    Args:
        pooled: Pooled effect estimate.
        se_pooled: Standard error of the pooled estimate.
        confidence_level: Confidence level (default 0.95).

    Returns:
        Tuple of (lower_bound, upper_bound).
    """
    alpha = 1.0 - confidence_level
    z = normal_quantile(1.0 - alpha / 2.0)
    margin = z * se_pooled
    return pooled - margin, pooled + margin


def compute_prediction_interval(
    pooled: float, se_pooled: float, tau_squared: float, k: int,
    confidence_level: float = 0.95
) -> tuple[float, float]:
    """Compute prediction interval for a new study's true effect.

    The prediction interval accounts for both sampling error and between-study
    heterogeneity: pooled ± t_(k-1) * sqrt(tau² + SE_pooled²)

    Args:
        pooled: Random-effects pooled estimate.
        se_pooled: Standard error of the pooled estimate.
        tau_squared: Between-study variance estimate.
        k: Number of studies.
        confidence_level: Confidence level (default 0.95).

    Returns:
        Tuple of (lower_bound, upper_bound) for the prediction interval.
    """
    df = k - 1
    alpha = 1.0 - confidence_level
    t_crit = t_quantile(1.0 - alpha / 2.0, df)
    pred_se = math.sqrt(tau_squared + se_pooled * se_pooled)
    return pooled - t_crit * pred_se, pooled + t_crit * pred_se


def normal_quantile(p: float) -> float:
    """Compute quantile of the standard normal distribution.

    Uses rational approximation (Abramowitz and Stegun).

    Args:
        p: Probability (0 < p < 1).

    Returns:
        z-value such that P(Z <= z) = p.
    """
    if p <= 0 or p >= 1:
        return 0.0

    if p < 0.5:
        return -_rational_approx(math.sqrt(-2.0 * math.log(p)))
    else:
        return _rational_approx(math.sqrt(-2.0 * math.log(1.0 - p)))


def _rational_approx(t: float) -> float:
    """Rational approximation for inverse normal CDF."""
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308
    return t - (c0 + c1 * t + c2 * t * t) / (1.0 + d1 * t + d2 * t * t + d3 * t * t * t)


def t_quantile(p: float, df: int) -> float:
    """Compute quantile of Student's t-distribution.

    Uses iterative Newton-Raphson refinement starting from normal approximation.

    Args:
        p: Probability (0 < p < 1).
        df: Degrees of freedom.

    Returns:
        t-value such that P(T <= t) = p for t-distribution with df degrees of freedom.
    """
    if df <= 0:
        return normal_quantile(p)

    if df == 1:
        return math.tan(math.pi * (p - 0.5))

    if df == 2:
        return (2.0 * p - 1.0) / math.sqrt(2.0 * p * (1.0 - p))

    z = normal_quantile(p)
    g1 = (z * z * z + z) / 4.0
    g2 = (5 * z ** 5 + 16 * z ** 3 + 3 * z) / 96.0
    g3 = (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / 384.0

    t = z + g1 / df + g2 / (df * df) + g3 / (df ** 3)
    return t


def run_random_effects_analysis(
    effects: list[float], std_errors: list[float]
) -> dict[str, Any]:
    """Execute full random-effects meta-analysis.

    Computes heterogeneity statistics, random-effects pooled estimate,
    confidence interval, and prediction interval.

    Args:
        effects: List of study effect sizes.
        std_errors: List of standard errors.

    Returns:
        Dictionary with complete random-effects analysis results.
    """
    k = len(effects)
    het = estimate_heterogeneity(effects, std_errors)
    tau_sq = het["tau_squared"]

    re_weights = compute_random_effects_weights(std_errors, tau_sq)
    pooled, se_pooled = compute_pooled_estimate(effects, re_weights)
    ci_lower, ci_upper = compute_confidence_interval(pooled, se_pooled)
    pi_lower, pi_upper = compute_prediction_interval(pooled, se_pooled, tau_sq, k)

    fe_weights = compute_weights(std_errors)
    fe_pooled = compute_fixed_effect_estimate(effects, fe_weights)
    fe_se = math.sqrt(1.0 / sum(fe_weights))
    fe_ci_lower, fe_ci_upper = compute_confidence_interval(fe_pooled, fe_se)

    return {
        "random_effects": {
            "pooled_estimate": round(pooled, 6),
            "std_error": round(se_pooled, 6),
            "ci_lower": round(ci_lower, 6),
            "ci_upper": round(ci_upper, 6),
            "prediction_interval_lower": round(pi_lower, 6),
            "prediction_interval_upper": round(pi_upper, 6),
            "num_studies": k,
        },
        "fixed_effect": {
            "pooled_estimate": round(fe_pooled, 6),
            "std_error": round(fe_se, 6),
            "ci_lower": round(fe_ci_lower, 6),
            "ci_upper": round(fe_ci_upper, 6),
        },
        "heterogeneity": het,
    }
