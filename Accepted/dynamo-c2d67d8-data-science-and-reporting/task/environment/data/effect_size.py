"""
Effect size module for the biostatistics pipeline.

Computes standardized effect size measures including Cohen's d,
confidence intervals for mean differences, and the Common Language
Effect Size (CLES / probability of superiority).
"""

import math


def compute_cohens_d(data_a, data_b):
    """
    Compute Cohen's d standardized effect size for two independent samples.

    Cohen's d measures the difference between two group means expressed
    in units of the pooled standard deviation. The pooled standard deviation
    uses the weighted average of within-group variances.

    Parameters
    ----------
    data_a : list of float
        Measurements from group A.
    data_b : list of float
        Measurements from group B.

    Returns
    -------
    float
        Cohen's d value. Positive values indicate group A > group B.
    """
    n_a = len(data_a)
    n_b = len(data_b)

    mean_a = sum(data_a) / n_a
    mean_b = sum(data_b) / n_b

    # Compute within-group sum of squares
    ss_a = sum((x - mean_a) ** 2 for x in data_a)
    ss_b = sum((x - mean_b) ** 2 for x in data_b)

    # Pooled standard deviation
    pooled_var = (ss_a + ss_b) / (n_a + n_b)
    pooled_sd = math.sqrt(pooled_var)

    if pooled_sd == 0:
        return 0.0

    d = (mean_a - mean_b) / pooled_sd

    return round(d, 10)


def compute_confidence_interval(data_a, data_b, confidence_level=0.95):
    """
    Compute the confidence interval for the difference in means between
    two independent groups using the pooled standard error.

    Parameters
    ----------
    data_a : list of float
        Measurements from group A.
    data_b : list of float
        Measurements from group B.
    confidence_level : float
        Confidence level (e.g., 0.95 for 95% CI).

    Returns
    -------
    tuple of (float, float)
        Lower and upper bounds of the confidence interval.
    """
    n_a = len(data_a)
    n_b = len(data_b)

    mean_a = sum(data_a) / n_a
    mean_b = sum(data_b) / n_b
    mean_diff = mean_a - mean_b

    # Compute variances
    var_a = sum((x - mean_a) ** 2 for x in data_a) / (n_a - 1)
    var_b = sum((x - mean_b) ** 2 for x in data_b) / (n_b - 1)

    # Standard error of the difference
    se_diff = math.sqrt(var_a / n_a + var_b / n_b)

    # Degrees of freedom (Welch-Satterthwaite)
    se_a = var_a / n_a
    se_b = var_b / n_b
    if (se_a + se_b) == 0:
        df = n_a + n_b - 2
    else:
        df = ((se_a + se_b) ** 2) / (
            (se_a ** 2) / (n_a - 1) + (se_b ** 2) / (n_b - 1)
        )

    # Critical t-value
    alpha = 1.0 - confidence_level
    t_crit = _inverse_t(1.0 - alpha / 2.0, df)

    margin = t_crit * se_diff
    ci_lower = mean_diff - margin
    ci_upper = mean_diff + margin

    return round(ci_lower, 10), round(ci_upper, 10)


def compute_common_language_effect(data_a, data_b):
    """
    Compute the Common Language Effect Size (CLES), also known as the
    probability of superiority.

    CLES represents the probability that a randomly selected observation
    from group A will be greater than a randomly selected observation
    from group B.

    Parameters
    ----------
    data_a : list of float
        Measurements from group A.
    data_b : list of float
        Measurements from group B.

    Returns
    -------
    float
        Probability of superiority (between 0 and 1).
    """
    n_a = len(data_a)
    n_b = len(data_b)

    count_superior = 0
    count_ties = 0

    for a_val in data_a:
        for b_val in data_b:
            if a_val > b_val:
                count_superior += 1
            elif a_val == b_val:
                count_ties += 1

    # Ties count as half a win
    cles = (count_superior + 0.5 * count_ties) / (n_a * n_b)

    return round(cles, 10)


def compute_hedges_g(data_a, data_b):
    """
    Compute Hedges' g, a bias-corrected version of Cohen's d.

    Applies the small-sample correction factor J to Cohen's d to reduce
    positive bias in small samples.

    Parameters
    ----------
    data_a : list of float
        Measurements from group A.
    data_b : list of float
        Measurements from group B.

    Returns
    -------
    float
        Hedges' g value.
    """
    d = compute_cohens_d(data_a, data_b)
    n_a = len(data_a)
    n_b = len(data_b)

    # Correction factor J (approximation for small samples)
    df = n_a + n_b - 2
    if df <= 0:
        return d

    j = 1.0 - (3.0 / (4.0 * df - 1.0))
    g = d * j

    return round(g, 10)


def compute_eta_squared(data_groups):
    """
    Compute eta-squared (η²) for one-way ANOVA-style effect size.

    Represents the proportion of total variance explained by
    group membership.

    Parameters
    ----------
    data_groups : list of list of float
        List of measurement lists, one per group.

    Returns
    -------
    float
        Eta-squared value between 0 and 1.
    """
    all_values = []
    for group in data_groups:
        all_values.extend(group)

    grand_mean = sum(all_values) / len(all_values)

    # Sum of squares between groups
    ss_between = 0.0
    for group in data_groups:
        group_mean = sum(group) / len(group)
        ss_between += len(group) * (group_mean - grand_mean) ** 2

    # Total sum of squares
    ss_total = sum((x - grand_mean) ** 2 for x in all_values)

    if ss_total == 0:
        return 0.0

    eta_sq = ss_between / ss_total
    return round(eta_sq, 10)


def _inverse_t(p, df):
    """
    Approximate the inverse of the t-distribution CDF (quantile function)
    using the Wilson-Hilferty approximation via the normal distribution.

    Parameters
    ----------
    p : float
        Probability (0 < p < 1).
    df : float
        Degrees of freedom.

    Returns
    -------
    float
        The t-value such that P(T <= t) = p.
    """
    # First get the normal quantile
    z = _inverse_normal(p)

    # Cornish-Fisher expansion for t from z
    g1 = (z ** 3 + z) / (4 * df)
    g2 = (5 * z ** 5 + 16 * z ** 3 + 3 * z) / (96 * df ** 2)
    g3 = (3 * z ** 7 + 19 * z ** 5 + 17 * z ** 3 - 15 * z) / (384 * df ** 3)

    t = z + g1 + g2 + g3
    return t


def _inverse_normal(p):
    """
    Approximate the inverse of the standard normal CDF using the
    rational approximation by Abramowitz and Stegun.
    """
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0
    if p == 0.5:
        return 0.0

    if p < 0.5:
        return -_rational_approx(math.sqrt(-2.0 * math.log(p)))
    else:
        return _rational_approx(math.sqrt(-2.0 * math.log(1.0 - p)))


def _rational_approx(t):
    """Helper for inverse normal computation."""
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    return t - (c0 + c1 * t + c2 * t ** 2) / (
        1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3
    )
