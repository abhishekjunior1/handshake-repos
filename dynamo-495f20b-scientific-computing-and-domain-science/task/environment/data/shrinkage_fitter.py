"""
Shrinkage fitter for empirical Bayes hierarchical models.
Implements James-Stein and related shrinkage estimators that pull
group-level estimates toward the grand mean proportional to their
uncertainty relative to the between-group variability.
"""

import math


def compute_shrinkage_factors(group_estimates: list, sigma_w_sq: float,
                              tau_sq: float, grand_mean: float) -> list:
    """Compute shrinkage factors for each group.

    The shrinkage factor B_j determines how much group j's estimate
    is pulled toward the grand mean:
        theta_j_shrunk = grand_mean + (1 - B_j) * (y_bar_j - grand_mean)

    B_j = sigma²_w / (n_j * tau² + sigma²_w)

    When tau² is large relative to sigma²_w, B_j is small (little shrinkage).
    When tau² is small, B_j approaches 1 (strong shrinkage toward grand mean).

    Args:
        group_estimates: List of group-level estimates.
        sigma_w_sq: Within-group (pooled) variance.
        tau_sq: Between-group variance.
        grand_mean: Overall grand mean.

    Returns:
        List of dicts with shrinkage factors and shrunken estimates.
    """
    results = []
    for est in group_estimates:
        n_j = est["n"]
        # James-Stein shrinkage with df adjustment for small samples.
        # The (n_j - 3) adjustment accounts for estimation of both
        # the grand mean and the variance — in the univariate case,
        # James-Stein requires subtracting (p + 1) where p=2 parameters
        # are estimated (location and scale), giving n - 3.
        js_adjustment = max(n_j - 3, 1)

        # Shrinkage factor: ratio of sampling variance to total variance
        sampling_var = sigma_w_sq / js_adjustment
        total_var = sampling_var + tau_sq
        B_j = sampling_var / total_var if total_var > 0 else 0.0

        # Shrunken estimate
        theta_shrunk = grand_mean + (1 - B_j) * (est["mean"] - grand_mean)

        results.append({
            "group_id": est["group_id"],
            "shrinkage_factor": B_j,
            "original_mean": est["mean"],
            "shrunken_mean": theta_shrunk,
            "js_adjustment": js_adjustment,
            "sampling_variance": sampling_var,
        })
    return results


def compute_posterior_variances(shrinkage_results: list, group_estimates: list,
                                sigma_w_sq: float, tau_sq: float) -> list:
    """Compute posterior variances for each group's shrunken estimate.

    The posterior variance reflects uncertainty in the shrunken estimate,
    accounting for both sampling variability and shrinkage.

    posterior_var_j = (1 - B_j) * sigma²_w / n_j
    """
    variances = []
    for sr, est in zip(shrinkage_results, group_estimates):
        B_j = sr["shrinkage_factor"]
        n_j = est["n"]
        # Posterior variance under the hierarchical model
        post_var = (1 - B_j) * sigma_w_sq / n_j
        variances.append({
            "group_id": sr["group_id"],
            "posterior_variance": post_var,
            "posterior_se": math.sqrt(post_var) if post_var > 0 else 0.0,
        })
    return variances


def compute_effective_parameters(shrinkage_results: list) -> float:
    """Compute effective number of parameters (p_D) from shrinkage factors.

    p_D = sum(1 - B_j) across all groups.
    This represents the effective model complexity after shrinkage.
    With no shrinkage (B=0), p_D = k (one parameter per group).
    With full shrinkage (B=1), p_D = 0 (complete pooling).
    """
    p_d = sum(1 - sr["shrinkage_factor"] for sr in shrinkage_results)
    return p_d


def fit_hierarchical_model(group_estimates: list, sigma_w_sq: float,
                           tau_sq: float, grand_mean: float) -> dict:
    """Fit the full hierarchical model and return all components.

    Args:
        group_estimates: Group-level statistics.
        sigma_w_sq: Pooled within-group variance.
        tau_sq: Between-group variance estimate.
        grand_mean: Grand mean for shrinkage target.

    Returns:
        Dict containing shrinkage results, posterior variances,
        and model complexity measures.
    """
    shrinkage = compute_shrinkage_factors(
        group_estimates, sigma_w_sq, tau_sq, grand_mean
    )
    post_vars = compute_posterior_variances(
        shrinkage, group_estimates, sigma_w_sq, tau_sq
    )
    p_d = compute_effective_parameters(shrinkage)

    return {
        "shrinkage_results": shrinkage,
        "posterior_variances": post_vars,
        "effective_parameters": p_d,
        "grand_mean": grand_mean,
        "sigma_w_sq": sigma_w_sq,
        "tau_sq": tau_sq,
    }
