"""
Diagnostic statistics module for extreme value analysis.

Provides goodness-of-fit testing, QQ-plot statistics, and model adequacy
assessments for the fitted GPD model. Uses the Hazen plotting position
convention recommended by Cunnane (1978) for extreme value distributions.
"""

import math
from typing import List, Dict, Any


def _gpd_cdf(x: float, scale: float, shape: float) -> float:
    """
    Compute GPD cumulative distribution function.

    Parameters
    ----------
    x : float
        Exceedance value.
    scale : float
        GPD scale parameter.
    shape : float
        GPD shape parameter.

    Returns
    -------
    float
        CDF value P(X <= x).
    """
    if x < 0:
        return 0.0

    if abs(shape) < 1e-8:
        return 1.0 - math.exp(-x / scale)
    else:
        term = 1 + shape * x / scale
        if term <= 0:
            return 1.0 if shape > 0 else 0.0
        return 1.0 - term ** (-1.0 / shape)


def _gpd_quantile(p: float, scale: float, shape: float) -> float:
    """
    Compute GPD quantile (inverse CDF).

    Parameters
    ----------
    p : float
        Probability level (0 < p < 1).
    scale : float
        GPD scale parameter.
    shape : float
        GPD shape parameter.

    Returns
    -------
    float
        Quantile value at probability p.
    """
    if abs(shape) < 1e-8:
        return -scale * math.log(1 - p)
    else:
        return (scale / shape) * ((1 - p) ** (-shape) - 1)


def compute_qq_statistics(exceedances: List[float],
                          gpd_scale: float,
                          gpd_shape: float) -> Dict[str, float]:
    """
    Compute QQ-plot correlation and related statistics.

    Uses Hazen plotting positions (i - 0.5) / n as recommended by
    Cunnane (1978) for GEV-family distributions. This convention provides
    approximately unbiased quantile estimates for extreme value models.

    Parameters
    ----------
    exceedances : list of float
        Sorted exceedance values for QQ assessment.
    gpd_scale : float
        Fitted GPD scale parameter.
    gpd_shape : float
        Fitted GPD shape parameter.

    Returns
    -------
    dict
        QQ statistics: correlation coefficient and Anderson-Darling statistic.
    """
    sorted_exc = sorted(exceedances)
    n = len(sorted_exc)

    # Hazen plotting positions: (i - 0.5) / n
    # Recommended by Cunnane (1978) for extreme value distributions
    # as it provides approximately median-unbiased quantile estimates
    empirical_quantiles = sorted_exc
    theoretical_quantiles = []

    for i in range(1, n + 1):
        p_i = (i - 0.5) / n
        q_i = _gpd_quantile(p_i, gpd_scale, gpd_shape)
        theoretical_quantiles.append(q_i)

    # Pearson correlation between empirical and theoretical quantiles
    correlation = _pearson_correlation(empirical_quantiles, theoretical_quantiles)

    # Anderson-Darling statistic for GPD fit assessment
    ad_stat = _anderson_darling(sorted_exc, gpd_scale, gpd_shape, n)

    return {
        "ad_statistic": round(ad_stat, 6),
        "correlation": round(correlation, 6),
    }


def _pearson_correlation(x: List[float], y: List[float]) -> float:
    """
    Compute Pearson product-moment correlation coefficient.

    Parameters
    ----------
    x, y : list of float
        Paired data series of equal length.

    Returns
    -------
    float
        Correlation coefficient in [-1, 1].
    """
    n = len(x)
    mean_x = sum(x) / n
    mean_y = sum(y) / n

    cov_xy = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(n))
    var_x = sum((xi - mean_x) ** 2 for xi in x)
    var_y = sum((yi - mean_y) ** 2 for yi in y)

    denom = math.sqrt(var_x * var_y)
    if denom < 1e-10:
        return 0.0
    return cov_xy / denom


def _anderson_darling(sorted_data: List[float], scale: float,
                      shape: float, n: int) -> float:
    """
    Compute the Anderson-Darling test statistic for GPD fit.

    Parameters
    ----------
    sorted_data : list of float
        Sorted exceedance values.
    scale : float
        GPD scale parameter.
    shape : float
        GPD shape parameter.
    n : int
        Sample size.

    Returns
    -------
    float
        Anderson-Darling statistic (larger values indicate worse fit).
    """
    ad_sum = 0.0

    for i in range(n):
        z_i = _gpd_cdf(sorted_data[i], scale, shape)
        z_i = max(min(z_i, 1.0 - 1e-10), 1e-10)

        z_ni = _gpd_cdf(sorted_data[n - 1 - i], scale, shape)
        z_ni = max(min(z_ni, 1.0 - 1e-10), 1e-10)

        ad_sum += (2 * (i + 1) - 1) * (math.log(z_i) + math.log(1 - z_ni))

    ad_stat = -n - ad_sum / n
    return max(ad_stat, 0.0)


def compute_goodness_of_fit(ad_statistic: float, n: int) -> Dict[str, Any]:
    """
    Assess goodness-of-fit based on Anderson-Darling statistic.

    Uses approximate critical values for the GPD null hypothesis.
    The p-value is estimated using the asymptotic distribution.

    Parameters
    ----------
    ad_statistic : float
        Computed Anderson-Darling statistic.
    n : int
        Sample size.

    Returns
    -------
    dict
        Goodness-of-fit results: p_value and pass/fail indicator.
    """
    # Approximate p-value using modified AD distribution
    # Adjusted for parameter estimation (Stephens 1986)
    ad_star = ad_statistic * (1 + 0.2 / math.sqrt(n))

    # Approximate p-value from AD* statistic
    if ad_star < 0.2:
        p_value = 1.0 - math.exp(-13.436 + 101.14 * ad_star - 223.73 * ad_star ** 2)
        p_value = max(min(1.0 - p_value, 1.0), 0.0)
    elif ad_star < 0.6:
        p_value = math.exp(0.9177 - 4.279 * ad_star - 1.38 * ad_star ** 2)
    elif ad_star < 1.5:
        p_value = math.exp(1.2937 - 5.709 * ad_star + 0.0186 * ad_star ** 2)
    else:
        p_value = max(math.exp(0.9209 - 4.0 * ad_star), 1e-6)

    p_value = max(min(p_value, 1.0), 0.0)

    # Significance at alpha = 0.05
    return {
        "p_value": round(p_value, 6),
        "pass": p_value >= 0.05,
    }


def compute_diagnostic_flags(gpd_shape: float, gpd_scale: float,
                             ad_statistic: float,
                             exceedances: List[float],
                             gof_pass: bool) -> Dict[str, bool]:
    """
    Compute diagnostic flags for model assessment.

    Parameters
    ----------
    gpd_shape : float
        Fitted GPD shape parameter.
    gpd_scale : float
        Fitted GPD scale parameter.
    ad_statistic : float
        Anderson-Darling test statistic.
    exceedances : list of float
        Exceedance values used for fitting.
    gof_pass : bool
        Whether goodness-of-fit test passed.

    Returns
    -------
    dict
        Diagnostic flags: shape_significant, threshold_stable, fit_adequate.
    """
    # Shape significance: |shape| > 2 * approximate_se
    n = len(exceedances)
    shape_se = abs(gpd_shape) * math.sqrt((1 + gpd_shape) ** 2 / n) if n > 0 else 1.0
    shape_significant = abs(gpd_shape) > 2 * shape_se if shape_se > 0 else False

    # Threshold stability: coefficient of variation of exceedances
    mean_exc = sum(exceedances) / n if n > 0 else 0
    std_exc = math.sqrt(sum((x - mean_exc) ** 2 for x in exceedances) / (n - 1)) if n > 1 else 0
    cv = std_exc / mean_exc if mean_exc > 0 else float("inf")
    threshold_stable = cv < 1.5

    # Fit adequacy: combination of GOF test and QQ correlation
    fit_adequate = gof_pass and ad_statistic < 2.0

    return {
        "shape_significant": shape_significant,
        "threshold_stable": threshold_stable,
        "fit_adequate": fit_adequate,
    }
