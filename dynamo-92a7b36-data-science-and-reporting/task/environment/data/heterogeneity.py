"""Heterogeneity estimation module for meta-analysis.

Implements Cochran's Q test, I-squared statistic, and the DerSimonian-Laird
estimator for between-study variance (tau-squared).
"""

import math
from typing import Any


def compute_weights(std_errors: list[float]) -> list[float]:
    """Compute inverse-variance weights for each study.

    Args:
        std_errors: List of standard errors for each study.

    Returns:
        List of weights where w_i = 1 / SE_i^2.
    """
    return [1.0 / (se * se) for se in std_errors]


def compute_fixed_effect_estimate(effects: list[float], weights: list[float]) -> float:
    """Compute the fixed-effect pooled estimate using inverse-variance weighting.

    Args:
        effects: List of study effect sizes.
        weights: List of inverse-variance weights.

    Returns:
        Weighted mean effect size under fixed-effect assumption.
    """
    numerator = sum(e * w for e, w in zip(effects, weights))
    denominator = sum(weights)
    return numerator / denominator


def compute_cochrans_q(
    effects: list[float], weights: list[float], pooled_estimate: float
) -> float:
    """Compute Cochran's Q statistic for heterogeneity.

    Q = sum(w_i * (theta_i - theta_hat)^2)

    Args:
        effects: List of study effect sizes.
        weights: List of inverse-variance weights.
        pooled_estimate: Fixed-effect pooled estimate.

    Returns:
        Cochran's Q statistic value.
    """
    q = sum(w * (e - pooled_estimate) ** 2 for e, w in zip(effects, weights))
    return q


def compute_i_squared(q: float, df: int) -> float:
    """Compute I-squared statistic measuring proportion of variance due to heterogeneity.

    I² = max(0, (Q - df) / Q) * 100

    Args:
        q: Cochran's Q statistic.
        df: Degrees of freedom (k - 1).

    Returns:
        I-squared as a percentage (0-100).
    """
    if q <= 0:
        return 0.0
    i_sq = max(0.0, (q - df) / q) * 100.0
    return i_sq


def compute_tau_squared(q: float, df: int, weights: list[float]) -> float:
    """Estimate between-study variance using the DerSimonian-Laird method.

    tau² = max(0, (Q - df) / C)
    where C = sum(w_i) - sum(w_i²) / sum(w_i) is the standard scaling
    factor for the moment-based estimator.

    Args:
        q: Cochran's Q statistic.
        df: Degrees of freedom (k - 1).
        weights: List of inverse-variance weights.

    Returns:
        Estimated between-study variance (tau-squared), non-negative.
    """
    sum_w = sum(weights)
    sum_w_sq = sum(w * w for w in weights)
    c = sum_w - sum_w_sq / sum_w

    if c <= 0:
        return 0.0

    tau_sq = (q - df) / c
    return max(0.0, tau_sq)


def q_test_p_value(q: float, df: int) -> float:
    """Compute p-value for Cochran's Q test using chi-squared distribution.

    Uses the regularized incomplete gamma function for the survival function.

    Args:
        q: Cochran's Q statistic.
        df: Degrees of freedom.

    Returns:
        P-value from chi-squared distribution with df degrees of freedom.
    """
    if df <= 0 or q <= 0:
        return 1.0
    return chi2_survival(q, df)


def chi2_survival(x: float, k: int) -> float:
    """Compute survival function (1 - CDF) of chi-squared distribution.

    Uses the relationship: P(X > x) = 1 - regularized_gamma(k/2, x/2)

    Args:
        x: Value at which to evaluate.
        k: Degrees of freedom.

    Returns:
        Probability that chi-squared(k) exceeds x.
    """
    return 1.0 - regularized_gamma_lower(k / 2.0, x / 2.0)


def regularized_gamma_lower(a: float, x: float) -> float:
    """Compute regularized lower incomplete gamma function P(a, x).

    Uses series expansion for convergence.

    Args:
        a: Shape parameter.
        x: Upper limit of integration.

    Returns:
        Value of the regularized lower incomplete gamma function.
    """
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0

    if x < a + 1:
        return gamma_series(a, x)
    else:
        return 1.0 - gamma_continued_fraction(a, x)


def gamma_series(a: float, x: float) -> float:
    """Evaluate regularized gamma using series expansion."""
    ln_gamma_a = math.lgamma(a)
    term = 1.0 / a
    total = term
    for n in range(1, 200):
        term *= x / (a + n)
        total += term
        if abs(term) < 1e-12 * abs(total):
            break
    return total * math.exp(-x + a * math.log(x) - ln_gamma_a)


def gamma_continued_fraction(a: float, x: float) -> float:
    """Evaluate complementary regularized gamma using continued fraction."""
    ln_gamma_a = math.lgamma(a)
    b = x + 1.0 - a
    c = 1.0 / 1e-30
    d = 1.0 / b
    h = d
    for i in range(1, 200):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < 1e-30:
            d = 1e-30
        c = b + an / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-12:
            break
    return h * math.exp(-x + a * math.log(x) - ln_gamma_a)


def estimate_heterogeneity(
    effects: list[float], std_errors: list[float]
) -> dict[str, Any]:
    """Run full heterogeneity analysis for a set of studies.

    Args:
        effects: List of study effect sizes.
        std_errors: List of standard errors.

    Returns:
        Dictionary containing Q statistic, degrees of freedom, p-value,
        I-squared, tau-squared, and the fixed-effect pooled estimate.
    """
    k = len(effects)
    df = k - 1
    weights = compute_weights(std_errors)
    pooled = compute_fixed_effect_estimate(effects, weights)
    q = compute_cochrans_q(effects, weights, pooled)
    p_value = q_test_p_value(q, df)
    i_sq = compute_i_squared(q, df)
    tau_sq = compute_tau_squared(q, df, weights)

    return {
        "Q": round(q, 6),
        "df": df,
        "p_value": round(p_value, 6),
        "I_squared": round(i_sq, 4),
        "tau_squared": round(tau_sq, 6),
        "fixed_effect_estimate": round(pooled, 6),
    }
