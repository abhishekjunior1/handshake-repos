"""
Hypothesis testing for experiment analysis.

Implements Welch's t-test for comparing two independent samples with
potentially unequal variances (the modern default over Student's t-test).

Uses the Welch-Satterthwaite approximation for degrees of freedom and
a rational approximation for the t-distribution CDF.
"""

import math


def welch_t_test(stats_control, stats_treatment):
    """Perform Welch's t-test for difference in means.

    Welch's t-test does NOT assume equal variances between groups.
    It uses the Welch-Satterthwaite equation for degrees of freedom,
    which adjusts for unequal variances and sample sizes.

    This is preferred over Student's t-test because:
    - It is valid whether variances are equal or not
    - Student's t-test is a special case when variances ARE equal
    - Using Welch's never hurts and often helps (Ruxton 2006)

    Args:
        stats_control: Control group statistics (mean, variance, n)
        stats_treatment: Treatment group statistics

    Returns:
        Dictionary with t_statistic, df, p_value
    """
    n_c = stats_control['n']
    n_t = stats_treatment['n']
    mean_c = stats_control['mean']
    mean_t = stats_treatment['mean']
    var_c = stats_control['variance']
    var_t = stats_treatment['variance']

    if n_c < 2 or n_t < 2:
        return {'t_statistic': 0.0, 'df': 1.0, 'p_value': 1.0}

    # Standard error of the difference
    se = math.sqrt(var_c / n_c + var_t / n_t)

    if se < 1e-15:
        return {'t_statistic': 0.0, 'df': n_c + n_t - 2, 'p_value': 1.0}

    # t-statistic
    t_stat = (mean_t - mean_c) / se

    # Welch-Satterthwaite degrees of freedom
    num = (var_c / n_c + var_t / n_t) ** 2
    denom = ((var_c / n_c) ** 2 / (n_c - 1) + (var_t / n_t) ** 2 / (n_t - 1))

    if denom < 1e-15:
        df = n_c + n_t - 2
    else:
        df = num / denom

    # Two-sided p-value
    p_value = _t_distribution_p_value(abs(t_stat), df)

    return {
        't_statistic': t_stat,
        'df': df,
        'p_value': p_value
    }


def _t_distribution_p_value(t_abs, df):
    """Compute two-sided p-value from t-distribution.

    Uses the regularized incomplete beta function approximation.

    Args:
        t_abs: Absolute t-statistic value
        df: Degrees of freedom

    Returns:
        Two-sided p-value
    """
    # Use beta distribution relationship: P(T > t) = I_x(df/2, 1/2)
    # where x = df / (df + t^2)
    x = df / (df + t_abs ** 2)

    # Regularized incomplete beta function approximation
    p_one_sided = 0.5 * _regularized_beta(x, df / 2, 0.5)

    # Two-sided
    return 2 * p_one_sided


def _regularized_beta(x, a, b, n_terms=100):
    """Approximate regularized incomplete beta function I_x(a, b).

    Uses continued fraction expansion for numerical stability.

    Args:
        x: Value in [0, 1]
        a: Shape parameter
        b: Shape parameter
        n_terms: Number of terms in expansion

    Returns:
        Approximation of I_x(a, b)
    """
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0

    # Use continued fraction (Lentz's method)
    # For x < (a+1)/(a+b+2), use direct CF; otherwise use 1 - I_{1-x}(b,a)
    if x > (a + 1) / (a + b + 2):
        return 1.0 - _regularized_beta(1 - x, b, a, n_terms)

    # Front factor: x^a * (1-x)^b / (a * B(a,b))
    log_front = a * math.log(x) + b * math.log(1 - x)
    log_front -= math.log(a)
    log_front -= _log_beta(a, b)

    # Continued fraction
    cf = _beta_cf(x, a, b, n_terms)

    result = math.exp(log_front) * cf
    return max(0.0, min(1.0, result))


def _beta_cf(x, a, b, n_terms):
    """Evaluate continued fraction for incomplete beta."""
    tiny = 1e-30
    f = tiny
    c = tiny
    d = 0.0

    for m in range(n_terms):
        if m == 0:
            numerator = 1.0
        else:
            k = m
            if k % 2 == 0:
                j = k // 2
                numerator = (j * (b - j) * x) / ((a + 2*j - 1) * (a + 2*j))
            else:
                j = (k + 1) // 2
                numerator = -((a + j) * (a + b + j) * x) / ((a + 2*j) * (a + 2*j + 1))

        d = 1.0 + numerator * d
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d

        c = 1.0 + numerator / c
        if abs(c) < tiny:
            c = tiny

        f *= c * d

        if abs(c * d - 1.0) < 1e-10:
            break

    return f


def _log_beta(a, b):
    """Compute log of Beta function: log(B(a,b)) = lgamma(a) + lgamma(b) - lgamma(a+b)."""
    return math.lgamma(a) + math.lgamma(b) - math.lgamma(a + b)
