"""Hypothesis testing for A/B experiments.

Implements Welch's t-test for continuous metrics and z-test for proportions.
Welch's t-test (unequal variance assumption) is the modern default as it
provides valid inference regardless of whether population variances are equal.
"""

import math
from typing import Any


def run_hypothesis_test(
    control_obs: list[float],
    treatment_obs: list[float],
    metric_type: str,
    direction: str,
    alpha: float
) -> dict[str, Any]:
    """Run the appropriate hypothesis test based on metric type.
    
    For continuous metrics, uses Welch's t-test (unequal variance assumption).
    For proportion metrics, uses a two-proportion z-test.
    
    Parameters
    ----------
    control_obs : observations for control group
    treatment_obs : observations for treatment group
    metric_type : 'continuous' or 'proportion'
    direction : 'increase', 'decrease', or 'any' (determines one/two-tailed)
    alpha : significance level
    
    Returns dict with test_statistic, p_value, reject_null, and test_type.
    """
    if metric_type == "continuous":
        return _welch_t_test(control_obs, treatment_obs, direction, alpha)
    elif metric_type == "proportion":
        return _proportion_z_test(control_obs, treatment_obs, direction, alpha)
    else:
        raise ValueError(f"Unknown metric type: {metric_type}")


def _welch_t_test(
    control_obs: list[float],
    treatment_obs: list[float],
    direction: str,
    alpha: float
) -> dict[str, Any]:
    """Welch's t-test for difference in means (unequal variance assumption).
    
    Unlike Student's t-test which assumes equal population variances,
    Welch's t-test uses the Welch-Satterthwaite approximation for
    degrees of freedom, providing robust inference under heteroscedasticity.
    """
    from scipy import stats as scipy_stats
    
    n_c = len(control_obs)
    n_t = len(treatment_obs)
    
    mean_c = sum(control_obs) / n_c
    mean_t = sum(treatment_obs) / n_t
    
    var_c = sum((x - mean_c) ** 2 for x in control_obs) / (n_c - 1)
    var_t = sum((x - mean_t) ** 2 for x in treatment_obs) / (n_t - 1)
    
    # Standard error of the difference
    se_diff = math.sqrt(var_c / n_c + var_t / n_t)
    
    if se_diff == 0:
        return {
            "test_type": "welch_t_test",
            "test_statistic": 0.0,
            "p_value": 1.0,
            "reject_null": False,
            "degrees_of_freedom": n_c + n_t - 2
        }
    
    # Test statistic
    t_stat = (mean_t - mean_c) / se_diff
    
    # Welch-Satterthwaite degrees of freedom
    var_c_n = var_c / n_c
    var_t_n = var_t / n_t
    df_num = (var_c_n + var_t_n) ** 2
    df_den = (var_c_n ** 2) / (n_c - 1) + (var_t_n ** 2) / (n_t - 1)
    df = df_num / df_den if df_den > 0 else n_c + n_t - 2
    
    # P-value based on direction
    if direction == "increase":
        p_value = 1 - scipy_stats.t.cdf(t_stat, df)
    elif direction == "decrease":
        p_value = scipy_stats.t.cdf(t_stat, df)
    else:  # "any" - two-tailed
        p_value = 2 * (1 - scipy_stats.t.cdf(abs(t_stat), df))
    
    return {
        "test_type": "welch_t_test",
        "test_statistic": round(t_stat, 8),
        "p_value": round(p_value, 10),
        "reject_null": bool(p_value < alpha),
        "degrees_of_freedom": round(df, 4)
    }


def _proportion_z_test(
    control_obs: list[float],
    treatment_obs: list[float],
    direction: str,
    alpha: float
) -> dict[str, Any]:
    """Two-proportion z-test.
    
    Observations should be binary (0/1). Uses pooled proportion under
    the null hypothesis for standard error computation.
    """
    from scipy import stats as scipy_stats
    
    n_c = len(control_obs)
    n_t = len(treatment_obs)
    
    p_c = sum(control_obs) / n_c
    p_t = sum(treatment_obs) / n_t
    
    # Pooled proportion under H0
    p_pooled = (sum(control_obs) + sum(treatment_obs)) / (n_c + n_t)
    
    # Standard error under null
    se = math.sqrt(p_pooled * (1 - p_pooled) * (1/n_c + 1/n_t))
    
    if se == 0:
        return {
            "test_type": "proportion_z_test",
            "test_statistic": 0.0,
            "p_value": 1.0,
            "reject_null": False,
            "degrees_of_freedom": None
        }
    
    z_stat = (p_t - p_c) / se
    
    # P-value based on direction
    if direction == "increase":
        p_value = 1 - scipy_stats.norm.cdf(z_stat)
    elif direction == "decrease":
        p_value = scipy_stats.norm.cdf(z_stat)
    else:  # two-tailed
        p_value = 2 * (1 - scipy_stats.norm.cdf(abs(z_stat)))
    
    return {
        "test_type": "proportion_z_test",
        "test_statistic": round(z_stat, 8),
        "p_value": round(p_value, 10),
        "reject_null": bool(p_value < alpha),
        "degrees_of_freedom": None
    }
