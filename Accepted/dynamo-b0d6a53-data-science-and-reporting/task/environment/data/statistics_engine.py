"""
Sample statistics computation for experiment analysis.

Computes descriptive statistics (mean, variance, standard error) for
experiment groups and pooled estimates for two-sample comparisons.
"""

import math


def compute_sample_stats(data):
    """Compute sample statistics for a data array.

    Args:
        data: List of numeric observations

    Returns:
        Dictionary with mean, variance (sample), n, se, std
    """
    n = len(data)
    if n == 0:
        return {'mean': 0.0, 'variance': 0.0, 'n': 0, 'se': 0.0, 'std': 0.0}

    mean = sum(data) / n

    # Sample variance (Bessel's correction: divide by n-1)
    if n > 1:
        variance = sum((x - mean) ** 2 for x in data) / (n - 1)
    else:
        variance = 0.0

    std = math.sqrt(variance)
    se = std / math.sqrt(n) if n > 0 else 0.0

    return {
        'mean': mean,
        'variance': variance,
        'n': n,
        'se': se,
        'std': std
    }


def compute_pooled_variance(stats_a, stats_b):
    """Compute pooled variance across two groups.

    Uses weighted average of sample variances:
    s_p^2 = ((n_a - 1)*s_a^2 + (n_b - 1)*s_b^2) / (n_a + n_b - 2)

    Args:
        stats_a: Sample statistics for group A
        stats_b: Sample statistics for group B

    Returns:
        Pooled variance estimate (float)
    """
    n_a = stats_a['n']
    n_b = stats_b['n']

    if n_a + n_b <= 2:
        return 0.0

    pooled = ((n_a - 1) * stats_a['variance'] + (n_b - 1) * stats_b['variance']) / (n_a + n_b - 2)
    return pooled


def compute_pooled_se(stats_a, stats_b):
    """Compute standard error of the difference in means.

    SE = sqrt(var_a/n_a + var_b/n_b)

    This is the Welch (unequal variance) version.

    Args:
        stats_a: Sample statistics for group A
        stats_b: Sample statistics for group B

    Returns:
        Standard error of the difference (float)
    """
    n_a = stats_a['n']
    n_b = stats_b['n']

    if n_a == 0 or n_b == 0:
        return 0.0

    se = math.sqrt(stats_a['variance'] / n_a + stats_b['variance'] / n_b)
    return se
