"""
Effect size computation for experiment analysis.

Implements Hedges' g (bias-corrected standardized effect size) and
confidence intervals for mean differences.

Hedges' g applies a correction factor J to Cohen's d to remove the
positive bias that occurs in small samples. For large samples (n > 50),
g ≈ d. The correction is: g = d * J where J = 1 - 3/(4*df - 1).
"""

import math


def hedges_g(stats_control, stats_treatment):
    """Compute Hedges' g (bias-corrected effect size).

    Hedges' g = Cohen's d * J
    where:
        d = (mean_t - mean_c) / s_pooled
        J = 1 - 3 / (4*df - 1)   (correction factor)
        df = n_c + n_t - 2

    This is preferred over raw Cohen's d because it removes the
    small-sample positive bias. For n > 50, the difference is negligible.

    Args:
        stats_control: Control group statistics
        stats_treatment: Treatment group statistics

    Returns:
        Dictionary with hedges_g, cohens_d, correction_factor
    """
    n_c = stats_control['n']
    n_t = stats_treatment['n']
    mean_c = stats_control['mean']
    mean_t = stats_treatment['mean']
    var_c = stats_control['variance']
    var_t = stats_treatment['variance']

    df = n_c + n_t - 2

    # Pooled standard deviation
    if df <= 0:
        return {'hedges_g': 0.0, 'cohens_d': 0.0, 'correction_factor': 1.0}

    s_pooled = math.sqrt(((n_c - 1) * var_c + (n_t - 1) * var_t) / df)

    if s_pooled < 1e-15:
        return {'hedges_g': 0.0, 'cohens_d': 0.0, 'correction_factor': 1.0}

    # Cohen's d
    cohens_d = (mean_t - mean_c) / s_pooled

    # Hedges' correction factor
    correction = 1.0 - 3.0 / (4.0 * df - 1.0)

    # Hedges' g
    g = cohens_d * correction

    return {
        'hedges_g': g,
        'cohens_d': cohens_d,
        'correction_factor': correction
    }


def confidence_interval_difference(stats_a, stats_b, confidence_level):
    """Compute confidence interval for the difference in means.

    Uses the standard error of the difference:
        SE_diff = sqrt(var_a/n_a + var_b/n_b)
        CI = (mean_b - mean_a) ± z * SE_diff

    This is the CORRECT method for the CI of a difference.
    The caller is responsible for using this function appropriately.

    Args:
        stats_a: First group statistics (control)
        stats_b: Second group statistics (treatment)
        confidence_level: e.g., 0.95

    Returns:
        Dictionary with lower, upper, point_estimate
    """
    diff = stats_b['mean'] - stats_a['mean']

    se_diff = math.sqrt(
        stats_a['variance'] / stats_a['n'] + stats_b['variance'] / stats_b['n']
    )

    z = _z_for_confidence(confidence_level)
    margin = z * se_diff

    return {
        'lower': diff - margin,
        'upper': diff + margin,
        'point_estimate': diff
    }


def confidence_interval_individual(stats, confidence_level):
    """Compute confidence interval for a single group mean.

    CI = mean ± z * SE
    where SE = std / sqrt(n)

    Args:
        stats: Group statistics (mean, se, n)
        confidence_level: e.g., 0.95

    Returns:
        Dictionary with lower, upper
    """
    z = _z_for_confidence(confidence_level)
    margin = z * stats['se']

    return {
        'lower': stats['mean'] - margin,
        'upper': stats['mean'] + margin
    }


def _z_for_confidence(confidence_level):
    """Get z-value for a confidence level using normal approximation.

    Args:
        confidence_level: e.g., 0.95

    Returns:
        z-value (e.g., 1.96 for 95%)
    """
    p = (1 + confidence_level) / 2
    t = math.sqrt(-2 * math.log(1 - p))

    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    z = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)
    return z
