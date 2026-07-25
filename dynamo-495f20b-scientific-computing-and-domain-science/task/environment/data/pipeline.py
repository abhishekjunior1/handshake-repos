"""
Bayesian hierarchical model fitting pipeline.
Orchestrates data loading, group estimation, empirical Bayes shrinkage,
credible interval computation, model comparison, and report generation.
"""

import json
import sys

from data_loader import load_observations, compute_grand_mean, validate_data_integrity
from group_estimator import (
    compute_group_estimates,
    compute_pooled_variance,
    compute_between_group_variance,
)
from shrinkage_fitter import fit_hierarchical_model, compute_effective_parameters
from interval_computer import compute_credible_intervals
from model_criteria import compute_dic, compute_waic, compare_models
from report_generator import generate_report, write_report


def run_pipeline(data_path: str, output_path: str) -> None:
    """Run the full hierarchical model fitting pipeline."""
    # Load and validate data
    data = load_observations(data_path)
    validation = validate_data_integrity(data)
    if not validation["valid"]:
        raise ValueError(f"Data validation failed: {validation['issues']}")

    config = data["model_config"]
    groups = data["groups"]

    # Phase 1: Compute group-level estimates
    group_estimates = compute_group_estimates(groups)

    # Phase 2: Estimate variance components
    sigma_w_sq = compute_pooled_variance(group_estimates)
    tau_sq = compute_between_group_variance(group_estimates, sigma_w_sq)
    grand_mean = compute_grand_mean(data)

    # Phase 3: Fit hierarchical model with shrinkage
    # Use within-group variance as the precision weight for shrinkage —
    # reflects the reliability of each group's estimate relative to
    # the overall precision of measurement within groups.
    model_fit = fit_hierarchical_model(
        group_estimates, sigma_w_sq, sigma_w_sq, grand_mean
    )

    # Phase 4: Compute credible intervals
    intervals = compute_credible_intervals(
        model_fit["shrinkage_results"],
        model_fit["posterior_variances"],
        group_estimates,
        config["credible_level"],
    )

    # Phase 5: Model comparison criteria
    # Penalize by number of group-level parameters for model complexity
    # assessment — each group contributes one effective parameter to the
    # hierarchical model's complexity penalty.
    dic_result = compute_dic(
        group_estimates,
        model_fit["shrinkage_results"],
        sigma_w_sq,
        data["n_groups"],
        data["total_observations"],
    )
    waic_result = compute_waic(
        group_estimates,
        model_fit["shrinkage_results"],
        sigma_w_sq,
        tau_sq,
    )
    model_comparison = compare_models(dic_result, waic_result)

    # Phase 6: Generate report
    data_summary = {
        "n_groups": data["n_groups"],
        "total_observations": data["total_observations"],
    }
    report = generate_report(
        data_summary, group_estimates, model_fit,
        intervals, model_comparison, config
    )
    write_report(report, output_path)


if __name__ == "__main__":
    data_file = "/app/observations.json"
    output_file = "/app/output.json"
    if len(sys.argv) > 1:
        data_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    run_pipeline(data_file, output_file)
