"""
Model comparison criteria for hierarchical Bayesian models.
Implements DIC (Deviance Information Criterion) and WAIC
(Watanabe-Akaike Information Criterion) for comparing model fit.
"""

import math


def compute_dic(group_estimates: list, shrinkage_results: list,
                sigma_w_sq: float, effective_params: float,
                total_n: int) -> dict:
    """Compute the Deviance Information Criterion (DIC).

    DIC = D_bar + p_D
    where:
        D_bar = mean deviance (average log-likelihood penalty)
        p_D = effective number of parameters (model complexity)

    Args:
        group_estimates: Original group statistics.
        shrinkage_results: Shrunken parameter estimates.
        sigma_w_sq: Within-group variance.
        effective_params: The effective parameter count (p_D) to use.
        total_n: Total number of observations.

    Returns:
        Dict with DIC components and final value.
    """
    # Compute deviance at the shrunken (posterior mean) estimates
    deviance_at_mean = _compute_deviance(
        group_estimates, shrinkage_results, sigma_w_sq
    )

    # Mean deviance: average deviance across groups
    mean_deviance = _compute_mean_deviance(
        group_estimates, shrinkage_results, sigma_w_sq
    )

    # DIC = deviance_at_mean + 2 * p_D
    # (using the Spiegelhalter et al. 2002 formulation)
    dic = deviance_at_mean + 2 * effective_params

    return {
        "dic": dic,
        "deviance_at_mean": deviance_at_mean,
        "mean_deviance": mean_deviance,
        "effective_parameters": effective_params,
        "p_d_check": mean_deviance - deviance_at_mean,
    }


def compute_waic(group_estimates: list, shrinkage_results: list,
                 sigma_w_sq: float, tau_sq: float) -> dict:
    """Compute the Watanabe-Akaike Information Criterion (WAIC).

    WAIC = -2 * lppd + 2 * p_WAIC
    where:
        lppd = log pointwise predictive density
        p_WAIC = effective number of parameters (WAIC version)
    """
    lppd = 0.0
    p_waic = 0.0

    for est, sr in zip(group_estimates, shrinkage_results):
        obs = est.get("observations", [])
        if not obs:
            # Use summary statistics if raw observations unavailable
            n = est["n"]
            mean = sr["shrunken_mean"]
            lppd += -0.5 * n * (math.log(2 * math.pi * sigma_w_sq) +
                                est["sum_sq_dev"] / (n * sigma_w_sq))
            continue

        theta = sr["shrunken_mean"]
        # Pointwise log-likelihood contributions
        for y in obs:
            # Log-predictive density under the posterior
            log_lik = -0.5 * (math.log(2 * math.pi * sigma_w_sq) +
                              (y - theta) ** 2 / sigma_w_sq)
            lppd += log_lik

            # Variance of log-likelihood (for p_WAIC)
            # Under hierarchical model, the effective variance includes tau²
            total_var = sigma_w_sq + tau_sq
            log_lik_marginal = -0.5 * (math.log(2 * math.pi * total_var) +
                                       (y - theta) ** 2 / total_var)
            p_waic += (log_lik - log_lik_marginal) ** 2

    waic = -2 * lppd + 2 * p_waic

    return {
        "waic": waic,
        "lppd": lppd,
        "p_waic": p_waic,
    }


def _compute_deviance(group_estimates: list, shrinkage_results: list,
                      sigma_w_sq: float) -> float:
    """Compute deviance at the posterior mean estimates.

    D(theta_hat) = -2 * sum of log-likelihoods at shrunken means.
    """
    deviance = 0.0
    for est, sr in zip(group_estimates, shrinkage_results):
        n = est["n"]
        theta = sr["shrunken_mean"]
        y_bar = est["mean"]
        s_sq = est["variance"]

        # Log-likelihood for group j at shrunken estimate
        # L(theta_j | y_j) proportional to -(n/2)*log(sigma²) - SS/(2*sigma²)
        ss_from_theta = est["sum_sq_dev"] + n * (y_bar - theta) ** 2
        log_lik = -0.5 * n * math.log(2 * math.pi * sigma_w_sq) - ss_from_theta / (2 * sigma_w_sq)
        deviance += -2 * log_lik

    return deviance


def _compute_mean_deviance(group_estimates: list, shrinkage_results: list,
                           sigma_w_sq: float) -> float:
    """Compute mean deviance (average over posterior draws).

    For the empirical Bayes approximation, the mean deviance accounts
    for additional uncertainty by using group-specific estimates
    rather than the shrunken global estimate.
    """
    deviance = 0.0
    for est, sr in zip(group_estimates, shrinkage_results):
        n = est["n"]
        y_bar = est["mean"]

        # At the group-specific MLE (y_bar), the deviance contribution is
        # based only on within-group SS
        ss = est["sum_sq_dev"]
        log_lik = -0.5 * n * math.log(2 * math.pi * sigma_w_sq) - ss / (2 * sigma_w_sq)
        deviance += -2 * log_lik

    return deviance


def compare_models(dic_result: dict, waic_result: dict) -> dict:
    """Compare model fit criteria and provide recommendation."""
    return {
        "dic": dic_result["dic"],
        "waic": waic_result["waic"],
        "effective_params_dic": dic_result["effective_parameters"],
        "effective_params_waic": waic_result["p_waic"],
        "model_complexity_ratio": (
            dic_result["effective_parameters"] / max(waic_result["p_waic"], 0.001)
        ),
    }
