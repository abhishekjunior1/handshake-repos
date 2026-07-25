"""
Generalized Pareto Distribution (GPD) parameter estimation module.

Implements maximum likelihood estimation for GPD parameters from threshold
exceedances. The GPD models the distribution of excesses above a high
threshold under the Pickands-Balkema-de Haan theorem.
"""

import math
from typing import List, Dict, Tuple


def _log_likelihood(exceedances: List[float], scale: float,
                    shape: float) -> float:
    """
    Compute GPD log-likelihood for given parameters.

    Parameters
    ----------
    exceedances : list of float
        Exceedance values.
    scale : float
        GPD scale parameter (sigma > 0).
    shape : float
        GPD shape parameter (xi).

    Returns
    -------
    float
        Log-likelihood value, or -inf if parameters are invalid.
    """
    n = len(exceedances)

    if scale <= 0:
        return float("-inf")

    log_lik = -n * math.log(scale)

    if abs(shape) < 1e-8:
        # Exponential case (shape = 0)
        log_lik -= sum(x / scale for x in exceedances)
    else:
        for x in exceedances:
            term = 1.0 + shape * x / scale
            if term <= 0:
                return float("-inf")
            log_lik -= (1.0 + 1.0 / shape) * math.log(term)

    return log_lik


def _mle_for_fixed_shape(exceedances: List[float], shape: float) -> float:
    """
    Compute the MLE scale parameter for a fixed shape value.

    For given xi, the profile MLE of sigma satisfies:
    sigma = (1+xi) * mean(x_i) when xi != 0 (approximate)

    More precisely, uses the score equation for sigma.

    Parameters
    ----------
    exceedances : list of float
        Exceedance values.
    shape : float
        Fixed GPD shape parameter.

    Returns
    -------
    float
        Optimal scale for the given shape.
    """
    n = len(exceedances)
    mean_x = sum(exceedances) / n

    if abs(shape) < 1e-8:
        # Exponential case: MLE of scale is the sample mean
        return mean_x

    # For GPD with shape xi, the profile MLE of sigma is found by
    # solving: n/sigma - (1+1/xi) * sum(x_i / (sigma + xi*x_i)) = 0
    # Use iterative fixed-point: sigma = (1+xi)/n * sum(x_i / (1+xi*x_i/sigma))
    sigma = mean_x * (1.0 + shape)  # Starting estimate
    sigma = max(sigma, 0.01)

    for _ in range(100):
        # Check support condition
        min_term = min(1.0 + shape * x / sigma for x in exceedances)
        if min_term <= 0:
            sigma = sigma * 1.5
            continue

        # Newton-type iteration for the scale score equation
        s1 = sum(exceedances[i] / (sigma + shape * exceedances[i])
                 for i in range(n))
        sigma_new = n / ((1.0 + 1.0 / shape) * s1) if abs(s1) > 1e-10 else sigma

        if sigma_new <= 0:
            sigma_new = sigma * 0.9

        if abs(sigma_new - sigma) < 1e-8 * sigma:
            break
        sigma = sigma_new

    return max(sigma, 1e-6)


def _profile_likelihood_search(exceedances: List[float]) -> Tuple[float, float]:
    """
    Find MLE parameters via profile likelihood over shape parameter.

    Evaluates the profile log-likelihood over a grid of shape values,
    computing the optimal scale for each, then refines the best.

    Parameters
    ----------
    exceedances : list of float
        Exceedance values.

    Returns
    -------
    tuple of (float, float)
        MLE (scale, shape) parameters.
    """
    best_ll = float("-inf")
    best_scale = sum(exceedances) / len(exceedances)
    best_shape = 0.0

    # Coarse grid search over shape parameter
    for shape_100 in range(-45, 46, 5):
        shape = shape_100 / 100.0
        scale = _mle_for_fixed_shape(exceedances, shape)
        ll = _log_likelihood(exceedances, scale, shape)
        if ll > best_ll:
            best_ll = ll
            best_scale = scale
            best_shape = shape

    # Fine grid refinement around best shape
    shape_low = best_shape - 0.05
    shape_high = best_shape + 0.05
    for shape_1000 in range(int(shape_low * 1000), int(shape_high * 1000) + 1, 5):
        shape = shape_1000 / 1000.0
        if shape > 0.5 or shape < -0.5:
            continue
        scale = _mle_for_fixed_shape(exceedances, shape)
        ll = _log_likelihood(exceedances, scale, shape)
        if ll > best_ll:
            best_ll = ll
            best_scale = scale
            best_shape = shape

    # Ultra-fine refinement
    shape_low = best_shape - 0.005
    shape_high = best_shape + 0.005
    for shape_10000 in range(int(shape_low * 10000), int(shape_high * 10000) + 1, 1):
        shape = shape_10000 / 10000.0
        if shape > 0.5 or shape < -0.5:
            continue
        scale = _mle_for_fixed_shape(exceedances, shape)
        ll = _log_likelihood(exceedances, scale, shape)
        if ll > best_ll:
            best_ll = ll
            best_scale = scale
            best_shape = shape

    return best_scale, best_shape


def estimate_gpd_parameters(exceedances: List[float]) -> Dict[str, float]:
    """
    Estimate GPD parameters from threshold exceedances.

    Uses profile maximum likelihood estimation with grid search over
    the shape parameter. Returns scale and shape parameters of the
    fitted GPD.

    Parameters
    ----------
    exceedances : list of float
        Exceedance values (obs - threshold for obs > threshold).

    Returns
    -------
    dict
        GPD parameters: scale (sigma) and shape (xi).
    """
    if len(exceedances) < 3:
        raise ValueError("Need at least 3 exceedances for GPD estimation.")

    # Profile likelihood MLE
    scale, shape = _profile_likelihood_search(exceedances)

    # Final bounds enforcement
    scale = max(scale, 1e-4)
    shape = max(min(shape, 0.5), -0.5)

    return {
        "scale": round(scale, 6),
        "shape": round(shape, 6),
    }
