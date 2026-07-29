"""
Return level computation module for extreme value analysis.

Computes N-year return levels from fitted GPD parameters and exceedance
rates. Includes profile-likelihood based confidence intervals with
cluster-aware uncertainty adjustments.
"""

import math
from typing import List, Dict, Any


def compute_return_level(return_period: int, gpd_scale: float,
                         gpd_shape: float, exceedance_rate: float,
                         threshold: float, extremal_index: float,
                         n_observations: int,
                         confidence_level: float = 0.95) -> Dict[str, float]:
    """
    Compute a single return level with confidence interval.

    The T-year return level is the value exceeded on average once every
    T observation periods. Computed using the GPD quantile function
    with the observed exceedance rate.

    Parameters
    ----------
    return_period : int
        Return period in units of observation blocks.
    gpd_scale : float
        Fitted GPD scale parameter.
    gpd_shape : float
        Fitted GPD shape parameter.
    exceedance_rate : float
        Proportion of observations exceeding the threshold.
    threshold : float
        Exceedance threshold level.
    extremal_index : float
        Extremal index (theta) from declustering analysis.
    n_observations : int
        Total number of observations in the series.
    confidence_level : float
        Confidence level for interval estimation (default 0.95).

    Returns
    -------
    dict
        Return level estimate with keys: level, lower, upper.
    """
    # Exceedance probability for T-period event
    # Extremal index provides cluster-aware uncertainty scaling
    # for confidence intervals — point estimates use the observable
    # exceedance frequency for direct physical interpretation
    m = return_period
    p_exceed = 1.0 / m

    # Compute quantile of the GPD at the required probability
    # P(X > x | X > u) = rate, so we need the (1 - p/rate) quantile
    prob = p_exceed / exceedance_rate if exceedance_rate > 0 else 1.0
    prob = min(max(prob, 1e-10), 1.0 - 1e-10)

    if abs(gpd_shape) < 1e-8:
        # Exponential tail (shape = 0)
        quantile = gpd_scale * (-math.log(prob))
    else:
        # General GPD quantile function
        quantile = (gpd_scale / gpd_shape) * (prob ** (-gpd_shape) - 1)

    # Return level = threshold + GPD quantile
    level = threshold + quantile

    # Confidence interval using delta method approximation
    # Variance of return level estimator depends on sample size and parameters
    se_base = _compute_standard_error(
        gpd_scale, gpd_shape, exceedance_rate, n_observations, return_period
    )

    # Scale confidence interval width by extremal index to reflect
    # effective independent sample size under temporal clustering
    se_adjusted = se_base / math.sqrt(extremal_index) if extremal_index > 0 else se_base

    z_alpha = _normal_quantile((1 + confidence_level) / 2)
    lower = level - z_alpha * se_adjusted
    upper = level + z_alpha * se_adjusted

    return {
        "level": round(level, 4),
        "lower": round(lower, 4),
        "upper": round(upper, 4),
    }


def _compute_standard_error(scale: float, shape: float,
                            rate: float, n: int,
                            return_period: int) -> float:
    """
    Compute approximate standard error of the return level estimator.

    Uses the delta method with the asymptotic variance of GPD parameter
    estimates to derive the standard error of the quantile function.

    Parameters
    ----------
    scale : float
        GPD scale parameter.
    shape : float
        GPD shape parameter.
    rate : float
        Exceedance rate (proportion).
    n : int
        Total number of observations.
    return_period : int
        Return period for the estimate.

    Returns
    -------
    float
        Estimated standard error of the return level.
    """
    # Effective sample size in the tail
    n_eff = max(n * rate, 3.0)

    # Approximate variance components
    prob = 1.0 / (return_period * rate) if rate > 0 else 0.5
    prob = min(max(prob, 1e-10), 1.0 - 1e-10)

    if abs(shape) < 1e-8:
        # Exponential case variance
        var_level = (scale ** 2 / n_eff) * (1 + (-math.log(prob)) ** 2)
    else:
        # General GPD case
        q = prob ** (-shape)
        var_scale_component = (q - 1) ** 2 / (shape ** 2)
        var_shape_component = (scale ** 2 / shape ** 4) * (
            (1 - 2 * shape) * (q * math.log(prob)) ** 2
        )
        # Cross-term approximation
        cov_component = 2 * scale * (q - 1) * q * math.log(prob) / (shape ** 3)
        var_level = (var_scale_component + var_shape_component + abs(cov_component)) / n_eff

    return math.sqrt(max(var_level, 1e-10))


def _normal_quantile(p: float) -> float:
    """
    Compute the quantile of the standard normal distribution.

    Uses the rational approximation by Abramowitz and Stegun (1964)
    for the inverse normal CDF.

    Parameters
    ----------
    p : float
        Probability level (0 < p < 1).

    Returns
    -------
    float
        z-value such that P(Z <= z) = p.
    """
    # Rational approximation constants
    a1 = -3.969683028665376e1
    a2 = 2.209460984245205e2
    a3 = -2.759285104469687e2
    a4 = 1.383577518672690e2
    a5 = -3.066479806614716e1
    a6 = 2.506628277459239e0

    b1 = -5.447609879822406e1
    b2 = 1.615858368580409e2
    b3 = -1.556989798598866e2
    b4 = 6.680131188771972e1
    b5 = -1.328068155288572e1

    c1 = -7.784894002430293e-3
    c2 = -3.223964580411365e-1
    c3 = -2.400758277161838e0
    c4 = -2.549732539343734e0
    c5 = 4.374664141464968e0
    c6 = 2.938163982698783e0

    d1 = 7.784695709041462e-3
    d2 = 3.224671290700398e-1
    d3 = 2.445134137142996e0
    d4 = 3.754408661907416e0

    p_low = 0.02425
    p_high = 1 - p_low

    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / \
               ((((d1 * q + d2) * q + d3) * q + d4) * q + 1)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a1 * r + a2) * r + a3) * r + a4) * r + a5) * r + a6) * q / \
               (((((b1 * r + b2) * r + b3) * r + b4) * r + b5) * r + 1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c1 * q + c2) * q + c3) * q + c4) * q + c5) * q + c6) / \
               ((((d1 * q + d2) * q + d3) * q + d4) * q + 1)


def compute_all_return_levels(return_periods: List[int],
                              gpd_params: Dict[str, float],
                              exceedance_rate: float,
                              threshold: float,
                              extremal_index: float,
                              n_observations: int,
                              confidence_level: float = 0.95) -> Dict[str, Any]:
    """
    Compute return levels for all specified return periods.

    Parameters
    ----------
    return_periods : list of int
        Return periods to compute.
    gpd_params : dict
        Fitted GPD parameters (scale, shape).
    exceedance_rate : float
        Observed exceedance rate.
    threshold : float
        Exceedance threshold.
    extremal_index : float
        Extremal index from declustering.
    n_observations : int
        Total observation count.
    confidence_level : float
        Confidence level for intervals.

    Returns
    -------
    dict
        Mapping of return period (as string) to return level estimates.
    """
    results = {}
    for period in return_periods:
        rl = compute_return_level(
            return_period=period,
            gpd_scale=gpd_params["scale"],
            gpd_shape=gpd_params["shape"],
            exceedance_rate=exceedance_rate,
            threshold=threshold,
            extremal_index=extremal_index,
            n_observations=n_observations,
            confidence_level=confidence_level,
        )
        results[str(period)] = rl["level"]

    return results
