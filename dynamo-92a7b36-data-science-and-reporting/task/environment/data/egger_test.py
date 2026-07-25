"""Egger's regression test for publication bias detection.

Implements the weighted linear regression of standardized effects on precision
to assess funnel plot asymmetry, indicating potential publication bias.
"""

import math
from typing import Any


def compute_precision(std_errors: list[float]) -> list[float]:
    """Compute precision (1/SE) for each study.

    Args:
        std_errors: List of standard errors.

    Returns:
        List of precision values.
    """
    return [1.0 / se for se in std_errors]


def compute_standardized_effects(
    effects: list[float], std_errors: list[float]
) -> list[float]:
    """Compute standardized effect sizes (effect / SE) for each study.

    Args:
        effects: List of effect sizes.
        std_errors: List of standard errors.

    Returns:
        List of standardized effect sizes.
    """
    return [e / se for e, se in zip(effects, std_errors)]


def weighted_least_squares(
    x: list[float], y: list[float], weights: list[float]
) -> tuple[float, float, float, float]:
    """Perform weighted least squares regression of y on x.

    Fits the model: y = intercept + slope * x with analytic weights.

    Args:
        x: Independent variable values (precision).
        y: Dependent variable values (standardized effects).
        weights: Regression weights for each observation.

    Returns:
        Tuple of (intercept, slope, se_intercept, se_slope).
    """
    n = len(x)
    sum_w = sum(weights)
    sum_wx = sum(w * xi for w, xi in zip(weights, x))
    sum_wy = sum(w * yi for w, yi in zip(weights, y))
    sum_wxx = sum(w * xi * xi for w, xi in zip(weights, x))
    sum_wxy = sum(w * xi * yi for w, xi, yi in zip(weights, x, y))

    denom = sum_w * sum_wxx - sum_wx * sum_wx
    if abs(denom) < 1e-15:
        return 0.0, 0.0, float("inf"), float("inf")

    slope = (sum_w * sum_wxy - sum_wx * sum_wy) / denom
    intercept = (sum_wy - slope * sum_wx) / sum_w

    residuals = [yi - intercept - slope * xi for xi, yi in zip(x, y)]
    sum_w_resid_sq = sum(w * r * r for w, r in zip(weights, residuals))

    if n <= 2:
        sigma_sq = 0.0
    else:
        sigma_sq = sum_w_resid_sq / (n - 2)

    se_intercept = math.sqrt(sigma_sq * sum_wxx / denom) if sigma_sq > 0 else float("inf")
    se_slope = math.sqrt(sigma_sq * sum_w / denom) if sigma_sq > 0 else float("inf")

    return intercept, slope, se_intercept, se_slope


def compute_t_statistic(estimate: float, std_error: float) -> float:
    """Compute t-statistic for a regression coefficient.

    Args:
        estimate: Coefficient estimate.
        std_error: Standard error of the coefficient.

    Returns:
        t-statistic value.
    """
    if std_error == float("inf") or std_error == 0:
        return 0.0
    return estimate / std_error


def t_distribution_p_value(t_stat: float, df: int) -> float:
    """Compute two-tailed p-value from t-distribution.

    Uses the relationship between t-distribution and regularized incomplete
    beta function.

    Args:
        t_stat: t-statistic value.
        df: Degrees of freedom.

    Returns:
        Two-tailed p-value.
    """
    if df <= 0:
        return 1.0
    x = df / (df + t_stat * t_stat)
    p = regularized_beta(x, df / 2.0, 0.5)
    return p


def regularized_beta(x: float, a: float, b: float) -> float:
    """Compute regularized incomplete beta function I_x(a, b).

    Uses continued fraction expansion for numerical evaluation.

    Args:
        x: Upper limit (0 <= x <= 1).
        a: First shape parameter.
        b: Second shape parameter.

    Returns:
        Value of the regularized incomplete beta function.
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    ln_beta = math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
    front = math.exp(math.log(x) * a + math.log(1 - x) * b - ln_beta)

    if x < (a + 1) / (a + b + 2):
        return front * beta_cf(x, a, b) / a
    else:
        return 1.0 - front * beta_cf(1 - x, b, a) / b


def beta_cf(x: float, a: float, b: float) -> float:
    """Evaluate continued fraction for incomplete beta function."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d

    for m in range(1, 200):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        h *= d * c

        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < 1e-30:
            d = 1e-30
        c = 1.0 + aa / c
        if abs(c) < 1e-30:
            c = 1e-30
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-10:
            break

    return h


def run_egger_test(effects: list[float], std_errors: list[float]) -> dict[str, Any]:
    """Run Egger's regression test for funnel plot asymmetry.

    Regresses standardized effects (effect/SE) on precision (1/SE) using
    weighted least squares. The weight for each study is the inverse of
    the sampling variance of the standardized effect. The intercept of
    this regression indicates potential publication bias.

    Args:
        effects: List of study effect sizes.
        std_errors: List of standard errors.

    Returns:
        Dictionary with intercept, slope, standard errors, t-statistics,
        p-values, and bias assessment.
    """
    k = len(effects)
    precision = compute_precision(std_errors)
    std_effects = compute_standardized_effects(effects, std_errors)

    # Weights for WLS: inverse of the variance of each standardized effect
    # The standardized effect z_i = theta_i / SE_i has variance that depends
    # on the sampling distribution of the effect estimate
    wls_weights = _compute_egger_weights(std_errors, effects)

    intercept, slope, se_intercept, se_slope = weighted_least_squares(
        precision, std_effects, wls_weights
    )

    t_intercept = compute_t_statistic(intercept, se_intercept)
    t_slope = compute_t_statistic(slope, se_slope)

    df = k - 2
    p_intercept = t_distribution_p_value(t_intercept, df)
    p_slope = t_distribution_p_value(t_slope, df)

    bias_detected = p_intercept < 0.10

    return {
        "intercept": round(intercept, 6),
        "slope": round(slope, 6),
        "se_intercept": round(se_intercept, 6),
        "se_slope": round(se_slope, 6),
        "t_intercept": round(t_intercept, 6),
        "t_slope": round(t_slope, 6),
        "p_intercept": round(p_intercept, 6),
        "p_slope": round(p_slope, 6),
        "df": df,
        "bias_detected": bias_detected,
    }


def _compute_egger_weights(std_errors: list[float], effects: list[float]) -> list[float]:
    """Compute regression weights for Egger's test.

    The standard Egger's test uses weights that are the inverse of the
    conditional variance of the standardized effect. For a study with
    standard error SE_i, the standardized effect z_i = theta_i/SE_i
    has variance that is approximated by the study's contribution
    to the overall precision.

    Args:
        std_errors: List of standard errors.
        effects: List of effect sizes.

    Returns:
        List of regression weights.
    """
    # Inverse of the variance contribution: proportional to precision squared
    total_precision = sum(1.0 / se for se in std_errors)
    weights = [(1.0 / se) / total_precision for se in std_errors]
    return weights
