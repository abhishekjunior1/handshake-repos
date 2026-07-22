"""
Statistical significance testing for model comparison.

Implements paired hypothesis tests for comparing model performance
across cross-validation folds. Uses fold-wise paired differences
to account for the correlation between models evaluated on the
same data splits.

Methodology:
- Paired t-test on fold differences: d_i = score_A[i] - score_B[i]
- Test H0: mean(d) = 0 vs H1: mean(d) != 0
- p-value from Student's t-distribution with df = n_folds - 1
- Bonferroni correction for multiple pairwise comparisons
"""

import math
from typing import Any


def compute_paired_differences(scores_a: list, scores_b: list) -> list:
    """Compute paired differences between two score vectors.

    For cross-validation, each element corresponds to the same fold,
    so differences capture the paired relationship.

    Args:
        scores_a: scores for model A, one per fold
        scores_b: scores for model B, one per fold

    Returns:
        list of fold-wise differences (a_i - b_i)
    """
    if len(scores_a) != len(scores_b):
        raise ValueError(
            f"Score vectors must have same length: {len(scores_a)} vs {len(scores_b)}"
        )
    return [a - b for a, b in zip(scores_a, scores_b)]


def compute_t_statistic(differences: list) -> tuple:
    """Compute t-statistic for paired differences.

    t = mean(d) / (std(d) / sqrt(n))

    Args:
        differences: list of paired differences

    Returns:
        (t_statistic, degrees_of_freedom)
    """
    n = len(differences)
    if n < 2:
        return (0.0, 0)

    mean_d = sum(differences) / n
    variance = sum((d - mean_d) ** 2 for d in differences) / (n - 1)
    std_d = math.sqrt(variance) if variance > 0 else 0.0

    if std_d < 1e-15:
        return (0.0, n - 1)

    se = std_d / math.sqrt(n)
    t_stat = mean_d / se

    return (t_stat, n - 1)


def t_distribution_cdf(t: float, df: int) -> float:
    """Approximate CDF of Student's t-distribution.

    Uses the regularized incomplete beta function approximation.
    For large df (>30), uses normal approximation.

    Args:
        t: t-statistic value
        df: degrees of freedom

    Returns:
        P(T <= t) for t-distribution with given df
    """
    if df <= 0:
        return 0.5

    if df > 30:
        return _normal_cdf(t)

    x = df / (df + t * t)
    prob = 0.5 * _regularized_incomplete_beta(df / 2.0, 0.5, x)

    if t >= 0:
        return 1.0 - prob
    else:
        return prob


def _normal_cdf(x: float) -> float:
    """Standard normal CDF approximation (Abramowitz and Stegun)."""
    if x < -8.0:
        return 0.0
    if x > 8.0:
        return 1.0

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1.0 if x >= 0 else -1.0
    x_abs = abs(x)

    t = 1.0 / (1.0 + p * x_abs)
    y = 1.0 - (((((a5 * t + a4) * t) + a3) * t + a2) * t + a1) * t * math.exp(-x_abs * x_abs / 2.0)

    return 0.5 * (1.0 + sign * y)


def _regularized_incomplete_beta(a: float, b: float, x: float) -> float:
    """Regularized incomplete beta function I_x(a, b).

    Uses continued fraction representation for numerical stability.
    """
    if x < 0.0 or x > 1.0:
        return 0.0
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0

    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _regularized_incomplete_beta(b, a, 1.0 - x)

    ln_prefix = (
        _log_gamma(a + b) - _log_gamma(a) - _log_gamma(b)
        + a * math.log(x) + b * math.log(1.0 - x)
    )
    prefix = math.exp(ln_prefix)

    cf = _continued_fraction_beta(a, b, x)
    return prefix * cf / a


def _continued_fraction_beta(a: float, b: float, x: float) -> float:
    """Evaluate continued fraction for incomplete beta function."""
    max_iter = 200
    eps = 1e-14

    qab = a + b
    qap = a + 1.0
    qam = a - 1.0

    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < 1e-30:
        d = 1e-30
    d = 1.0 / d
    h = d

    for m in range(1, max_iter + 1):
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

        if abs(delta - 1.0) < eps:
            break

    return h


def _log_gamma(x: float) -> float:
    """Stirling's approximation for log-gamma function."""
    if x <= 0:
        return 0.0

    if x < 0.5:
        return math.log(math.pi / math.sin(math.pi * x)) - _log_gamma(1.0 - x)

    x -= 1.0
    coefficients = [
        76.18009172947146,
        -86.50532032941677,
        24.01409824083091,
        -1.231739572450155,
        0.1208650973866179e-2,
        -0.5395239384953e-5
    ]

    tmp = x + 5.5
    tmp = (x + 0.5) * math.log(tmp) - tmp
    ser = 1.000000000190015

    for c in coefficients:
        x += 1.0
        ser += c / x

    return tmp + math.log(2.5066282746310005 * ser)


def compute_p_value(t_stat: float, df: int) -> float:
    """Compute two-tailed p-value from t-statistic.

    p = 2 * P(T > |t|) = 2 * (1 - CDF(|t|))

    Args:
        t_stat: t-statistic value
        df: degrees of freedom

    Returns:
        Two-tailed p-value in [0, 1]
    """
    if df <= 0:
        return 1.0

    cdf_value = t_distribution_cdf(abs(t_stat), df)
    p_value = 2.0 * (1.0 - cdf_value)

    return max(0.0, min(1.0, p_value))


def paired_t_test(scores_a: list, scores_b: list) -> dict:
    """Perform paired t-test comparing two models.

    Computes fold-wise differences, then tests if the mean
    difference is significantly different from zero.

    Args:
        scores_a: fold scores for model A
        scores_b: fold scores for model B

    Returns:
        dict with t_statistic, df, p_value, mean_difference, significant
    """
    differences = compute_paired_differences(scores_a, scores_b)
    t_stat, df = compute_t_statistic(differences)
    p_value = compute_p_value(t_stat, df)
    mean_diff = sum(differences) / len(differences) if differences else 0.0

    return {
        "t_statistic": t_stat,
        "df": df,
        "p_value": p_value,
        "mean_difference": mean_diff
    }


def apply_bonferroni_correction(p_values: list, n_comparisons: int) -> list:
    """Apply Bonferroni correction for multiple comparisons.

    Adjusts p-values by multiplying by the number of comparisons.
    Controls the family-wise error rate (FWER).

    Args:
        p_values: list of raw p-values
        n_comparisons: total number of pairwise comparisons

    Returns:
        list of corrected p-values (capped at 1.0)
    """
    return [min(p * n_comparisons, 1.0) for p in p_values]


def determine_significance(p_values: list, alpha: float) -> list:
    """Determine which comparisons are statistically significant.

    Args:
        p_values: list of (possibly corrected) p-values
        alpha: significance threshold

    Returns:
        list of booleans indicating significance
    """
    return [p < alpha for p in p_values]
