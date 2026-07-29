"""
Report generator for hierarchical Bayesian model analysis.
Produces a structured JSON report with model diagnostics,
parameter estimates, credible intervals, and model comparisons.
"""

import json


def generate_report(data_summary: dict, group_estimates: list,
                    model_fit: dict, intervals: list,
                    model_comparison: dict, config: dict) -> dict:
    """Generate the full model analysis report.

    Args:
        data_summary: Summary of input data.
        group_estimates: Original group-level statistics.
        model_fit: Hierarchical model fit results.
        intervals: Credible intervals per group.
        model_comparison: DIC/WAIC comparison results.
        config: Model configuration.

    Returns:
        Complete report dict for JSON serialization.
    """
    report = {
        "model_summary": _build_model_summary(data_summary, model_fit, config),
        "group_estimates": _build_group_estimates(
            group_estimates, model_fit, intervals
        ),
        "variance_components": _build_variance_components(model_fit),
        "model_comparison": model_comparison,
        "diagnostics": _build_diagnostics(model_fit, intervals),
    }
    return report


def _build_model_summary(data_summary: dict, model_fit: dict,
                         config: dict) -> dict:
    """Build the model summary section."""
    return {
        "n_groups": data_summary["n_groups"],
        "total_observations": data_summary["total_observations"],
        "estimation_method": config["estimation_method"],
        "shrinkage_type": config["shrinkage_type"],
        "credible_level": config["credible_level"],
        "grand_mean": model_fit["grand_mean"],
        "effective_parameters": model_fit["effective_parameters"],
    }


def _build_group_estimates(group_estimates: list, model_fit: dict,
                           intervals: list) -> list:
    """Build per-group estimate entries for the report."""
    entries = []
    shrinkage = model_fit["shrinkage_results"]
    post_vars = model_fit["posterior_variances"]

    for est, sr, pv, iv in zip(group_estimates, shrinkage, post_vars, intervals):
        entries.append({
            "group_id": est["group_id"],
            "n": est["n"],
            "sample_mean": round(est["mean"], 6),
            "sample_variance": round(est["variance"], 6),
            "shrinkage_factor": round(sr["shrinkage_factor"], 6),
            "shrunken_mean": round(sr["shrunken_mean"], 6),
            "posterior_se": round(pv["posterior_se"], 6),
            "ci_lower": round(iv["lower"], 6),
            "ci_upper": round(iv["upper"], 6),
            "ci_width": round(iv["width"], 6),
        })
    return entries


def _build_variance_components(model_fit: dict) -> dict:
    """Build variance decomposition section."""
    sigma_w = model_fit["sigma_w_sq"]
    tau = model_fit["tau_sq"]
    total = sigma_w + tau
    icc = tau / total if total > 0 else 0.0

    return {
        "within_group_variance": round(sigma_w, 6),
        "between_group_variance": round(tau, 6),
        "total_variance": round(total, 6),
        "intraclass_correlation": round(icc, 6),
    }


def _build_diagnostics(model_fit: dict, intervals: list) -> dict:
    """Build model diagnostics section."""
    shrinkage_factors = [
        sr["shrinkage_factor"] for sr in model_fit["shrinkage_results"]
    ]
    mean_shrinkage = (
        sum(shrinkage_factors) / len(shrinkage_factors)
        if shrinkage_factors else 0.0
    )

    widths = [iv["width"] for iv in intervals]
    mean_width = sum(widths) / len(widths) if widths else 0.0

    return {
        "mean_shrinkage_factor": round(mean_shrinkage, 6),
        "min_shrinkage_factor": round(min(shrinkage_factors), 6) if shrinkage_factors else 0.0,
        "max_shrinkage_factor": round(max(shrinkage_factors), 6) if shrinkage_factors else 0.0,
        "mean_interval_width": round(mean_width, 6),
        "effective_parameters": round(model_fit["effective_parameters"], 6),
    }


def write_report(report: dict, output_path: str) -> None:
    """Write report to JSON file."""
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
