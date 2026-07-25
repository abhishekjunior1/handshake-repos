"""Sample statistics computation for A/B test experiment analysis.

Computes descriptive statistics, standard errors, and confidence intervals
for control and treatment groups.
"""

import math
from typing import Any


def compute_sample_statistics(observations: list[float]) -> dict[str, float]:
    """Compute basic sample statistics for a group.
    
    Returns mean, variance (sample), standard deviation, standard error,
    and sample size.
    """
    n = len(observations)
    mean = sum(observations) / n
    
    # Sample variance with Bessel's correction
    variance = sum((x - mean) ** 2 for x in observations) / (n - 1)
    std_dev = math.sqrt(variance)
    se = std_dev / math.sqrt(n)
    
    return {
        "n": n,
        "mean": mean,
        "variance": variance,
        "std_dev": std_dev,
        "standard_error": se
    }


def compute_pooled_variance(control_obs: list[float], treatment_obs: list[float]) -> float:
    """Compute the pooled variance across both groups.
    
    Uses the weighted average of sample variances, appropriate when
    combining information across groups for power analysis.
    """
    n_c = len(control_obs)
    n_t = len(treatment_obs)
    
    mean_c = sum(control_obs) / n_c
    mean_t = sum(treatment_obs) / n_t
    
    ss_c = sum((x - mean_c) ** 2 for x in control_obs)
    ss_t = sum((x - mean_t) ** 2 for x in treatment_obs)
    
    pooled_var = (ss_c + ss_t) / (n_c + n_t - 2)
    return pooled_var


def compute_effect_size(control_stats: dict, treatment_stats: dict) -> dict[str, float]:
    """Compute effect size using Hedges' g (bias-corrected).
    
    Hedges' g applies a correction factor for small-sample bias,
    making it preferred over Cohen's d when sample sizes are modest.
    The correction factor J approaches 1 for large samples.
    """
    n_c = control_stats["n"]
    n_t = treatment_stats["n"]
    
    mean_diff = treatment_stats["mean"] - control_stats["mean"]
    
    # Pooled standard deviation (Cohen's d denominator)
    pooled_sd = math.sqrt(
        ((n_c - 1) * control_stats["variance"] + (n_t - 1) * treatment_stats["variance"])
        / (n_c + n_t - 2)
    )
    
    cohens_d = mean_diff / pooled_sd if pooled_sd > 0 else 0.0
    
    # Hedges' g correction factor for small-sample bias
    df = n_c + n_t - 2
    j_correction = 1 - (3 / (4 * df - 1))
    hedges_g = cohens_d * j_correction
    
    return {
        "cohens_d": cohens_d,
        "hedges_g": hedges_g,
        "pooled_sd": pooled_sd,
        "mean_difference": mean_diff
    }


def compute_confidence_interval_difference(
    control_stats: dict,
    treatment_stats: dict,
    confidence_level: float
) -> dict[str, float]:
    """Compute confidence interval for the difference in means.
    
    Uses the pooled standard error of the difference for constructing
    the interval around (mean_treatment - mean_control). This accounts
    for the combined uncertainty from both groups through the
    square root of the sum of squared standard errors.
    """
    from scipy import stats as scipy_stats
    
    n_c = control_stats["n"]
    n_t = treatment_stats["n"]
    mean_diff = treatment_stats["mean"] - control_stats["mean"]
    
    # Standard error of the difference (pooled SE)
    se_diff = math.sqrt(
        control_stats["variance"] / n_c + treatment_stats["variance"] / n_t
    )
    
    # Welch-Satterthwaite degrees of freedom for unequal variances
    var_c_n = control_stats["variance"] / n_c
    var_t_n = treatment_stats["variance"] / n_t
    
    numerator = (var_c_n + var_t_n) ** 2
    denominator = (var_c_n ** 2) / (n_c - 1) + (var_t_n ** 2) / (n_t - 1)
    df = numerator / denominator if denominator > 0 else n_c + n_t - 2
    
    alpha = 1 - confidence_level
    t_crit = scipy_stats.t.ppf(1 - alpha / 2, df)
    
    margin = t_crit * se_diff
    
    return {
        "mean_difference": mean_diff,
        "se_difference": se_diff,
        "ci_lower": mean_diff - margin,
        "ci_upper": mean_diff + margin,
        "df": df,
        "margin_of_error": margin
    }


def compute_group_confidence_interval(
    stats: dict,
    confidence_level: float
) -> dict[str, float]:
    """Compute confidence interval for a single group mean."""
    from scipy import stats as scipy_stats
    
    n = stats["n"]
    mean = stats["mean"]
    se = stats["standard_error"]
    
    alpha = 1 - confidence_level
    df = n - 1
    t_crit = scipy_stats.t.ppf(1 - alpha / 2, df)
    
    margin = t_crit * se
    
    return {
        "mean": mean,
        "ci_lower": mean - margin,
        "ci_upper": mean + margin,
        "margin_of_error": margin
    }
