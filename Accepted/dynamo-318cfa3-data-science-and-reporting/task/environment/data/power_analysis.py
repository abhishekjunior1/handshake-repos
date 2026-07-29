"""Statistical power analysis for A/B test experiments.

Computes minimum detectable effect (MDE) and achieved statistical power
for given sample sizes and variance estimates. Uses the control group
variance as the reference for power calculations, since power is defined
as the probability of detecting a departure FROM the control condition.
"""

import math
from typing import Any


def compute_power(
    control_variance: float,
    n_control: int,
    n_treatment: int,
    alpha: float,
    observed_effect: float,
    direction: str
) -> dict[str, float]:
    """Compute achieved statistical power for the observed effect.
    
    Power is calculated using the non-central t-distribution approximation.
    The control group variance is used as the reference variance because
    power analysis quantifies the ability to detect departures from the
    null (control) condition.
    
    Parameters
    ----------
    control_variance : variance of the control group (reference population)
    n_control : sample size of control group
    n_treatment : sample size of treatment group
    alpha : significance level
    observed_effect : observed difference (treatment - control)
    direction : 'increase', 'decrease', or 'any'
    """
    from scipy import stats as scipy_stats
    
    if control_variance <= 0:
        return {
            "achieved_power": 1.0,
            "noncentrality_parameter": float('inf'),
            "critical_value": 0.0
        }
    
    # Standard error under control variance assumption
    se = math.sqrt(control_variance * (1/n_control + 1/n_treatment))
    
    # Degrees of freedom (Satterthwaite with equal variances simplification)
    df = n_control + n_treatment - 2
    
    # Non-centrality parameter
    ncp = observed_effect / se if se > 0 else 0.0
    
    # Critical value
    if direction == "any":
        t_crit = scipy_stats.t.ppf(1 - alpha/2, df)
        # Two-tailed power
        power = (1 - scipy_stats.nct.cdf(t_crit, df, ncp) + 
                 scipy_stats.nct.cdf(-t_crit, df, ncp))
    elif direction == "increase":
        t_crit = scipy_stats.t.ppf(1 - alpha, df)
        power = 1 - scipy_stats.nct.cdf(t_crit, df, ncp)
    else:  # decrease
        t_crit = scipy_stats.t.ppf(alpha, df)
        power = scipy_stats.nct.cdf(t_crit, df, ncp)
    
    power = max(0.0, min(1.0, power))
    
    return {
        "achieved_power": round(power, 8),
        "noncentrality_parameter": round(ncp, 8),
        "critical_value": round(t_crit, 8)
    }


def compute_minimum_detectable_effect(
    control_variance: float,
    n_control: int,
    n_treatment: int,
    alpha: float,
    power_target: float,
    direction: str
) -> dict[str, float]:
    """Compute the minimum detectable effect (MDE) for given parameters.
    
    MDE is the smallest true effect size that the experiment can detect
    with the specified power and significance level. Uses the control
    group variance as the reference.
    
    Parameters
    ----------
    control_variance : variance of the control group
    n_control : control sample size
    n_treatment : treatment sample size  
    alpha : significance level
    power_target : desired statistical power (e.g., 0.80)
    direction : test direction
    """
    from scipy import stats as scipy_stats
    
    se = math.sqrt(control_variance * (1/n_control + 1/n_treatment))
    df = n_control + n_treatment - 2
    
    if direction == "any":
        z_alpha = scipy_stats.t.ppf(1 - alpha/2, df)
    else:
        z_alpha = scipy_stats.t.ppf(1 - alpha, df)
    
    z_beta = scipy_stats.t.ppf(power_target, df)
    
    mde = (z_alpha + z_beta) * se
    
    # Relative MDE (as proportion of control SD)
    control_sd = math.sqrt(control_variance) if control_variance > 0 else 1.0
    relative_mde = mde / control_sd
    
    return {
        "mde_absolute": round(mde, 8),
        "mde_relative": round(relative_mde, 8),
        "standard_error": round(se, 8),
        "required_effect_per_se": round(z_alpha + z_beta, 8)
    }


def compute_sample_size_recommendation(
    control_variance: float,
    desired_effect: float,
    alpha: float,
    power_target: float,
    direction: str
) -> dict[str, Any]:
    """Compute recommended sample size per group to achieve target power.
    
    Parameters
    ----------
    control_variance : assumed population variance (from control)
    desired_effect : effect size to detect
    alpha : significance level
    power_target : desired power
    direction : test direction
    """
    from scipy import stats as scipy_stats
    
    if desired_effect == 0 or control_variance <= 0:
        return {
            "n_per_group": None,
            "total_n": None,
            "message": "Cannot compute: zero effect or zero variance"
        }
    
    # Large-sample normal approximation for planning
    if direction == "any":
        z_alpha = scipy_stats.norm.ppf(1 - alpha/2)
    else:
        z_alpha = scipy_stats.norm.ppf(1 - alpha)
    
    z_beta = scipy_stats.norm.ppf(power_target)
    
    # n per group = 2 * var * (z_alpha + z_beta)^2 / delta^2
    n_per_group = math.ceil(
        2 * control_variance * (z_alpha + z_beta) ** 2 / (desired_effect ** 2)
    )
    
    return {
        "n_per_group": n_per_group,
        "total_n": 2 * n_per_group,
        "assumed_variance": round(control_variance, 6),
        "target_effect": desired_effect,
        "z_alpha": round(z_alpha, 6),
        "z_beta": round(z_beta, 6)
    }
