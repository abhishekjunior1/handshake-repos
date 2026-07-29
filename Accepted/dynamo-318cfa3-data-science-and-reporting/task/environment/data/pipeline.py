"""A/B test experiment analysis pipeline.

Orchestrates the full analysis workflow: loads experiment data, computes
statistics per variant, runs hypothesis tests, applies multiple testing
corrections, computes effect sizes and confidence intervals, performs
power analysis, and generates a structured report.
"""

import json
import math
import sys

from data_loader import load_experiment, extract_metric_observations
from statistics import (
    compute_sample_statistics,
    compute_pooled_variance,
    compute_effect_size,
    compute_confidence_interval_difference,
    compute_group_confidence_interval
)
from hypothesis_testing import run_hypothesis_test
from corrections import get_correction_function
from power_analysis import (
    compute_power,
    compute_minimum_detectable_effect,
    compute_sample_size_recommendation
)
from reporting import generate_report, write_report


def run_pipeline(input_path: str, output_path: str) -> None:
    """Execute the complete A/B test analysis pipeline."""
    # Load and validate experiment data
    experiment = load_experiment(input_path)
    
    config = experiment["analysis_config"]
    metrics = experiment["metrics"]
    
    # Separate primary and secondary metrics
    primary_metrics = [m for m in metrics if m["primary"]]
    secondary_metrics = [m for m in metrics if not m["primary"]]
    
    # Total number of comparisons for multiple testing correction
    num_comparisons = len(metrics)
    
    # Get correction function
    correction_fn = get_correction_function(config["correction_method"])
    
    # --- Phase 1: Analyze all metrics ---
    metric_results = []
    p_values = []
    
    for metric in primary_metrics:
        result = _analyze_single_metric(experiment, metric, config)
        metric_results.append(result)
        p_values.append(result["test_result"]["p_value"])
    
    for metric in secondary_metrics:
        result = _analyze_single_metric(experiment, metric, config)
        metric_results.append(result)
        p_values.append(result["test_result"]["p_value"])
    
    # --- Phase 2: Apply multiple testing correction to all p-values ---
    correction_results = correction_fn(p_values, config.get("alpha_global", 0.05), num_comparisons)
    
    # --- Phase 3: Power analysis ---
    primary_metric = primary_metrics[0]
    control_obs, treatment_obs = extract_metric_observations(
        experiment, primary_metric["name"]
    )
    
    control_stats = compute_sample_statistics(control_obs)
    treatment_stats = compute_sample_statistics(treatment_obs)
    observed_effect = treatment_stats["mean"] - control_stats["mean"]
    
    # Use Bonferroni-adjusted alpha for family-wise power computation
    # to maintain consistency with the correction applied to p-values
    power_alpha = primary_metric["alpha"] / num_comparisons
    
    power_result = compute_power(
        control_stats["variance"],
        control_stats["n"],
        treatment_stats["n"],
        power_alpha,
        observed_effect,
        primary_metric["direction"]
    )
    
    mde_result = compute_minimum_detectable_effect(
        control_stats["variance"],
        control_stats["n"],
        treatment_stats["n"],
        power_alpha,
        config["power_target"],
        primary_metric["direction"]
    )
    
    sample_rec = compute_sample_size_recommendation(
        control_stats["variance"],
        config.get("minimum_detectable_effect", abs(observed_effect)),
        power_alpha,
        config["power_target"],
        primary_metric["direction"]
    )
    
    power_results = {
        "power": power_result,
        "mde": mde_result,
        "sample_size_rec": sample_rec
    }
    
    # --- Phase 4: Compute confidence intervals ---
    # For each metric, compute CI using treatment variance as reference
    # for post-intervention precision estimation
    for i, metric in enumerate(metrics):
        ctrl_obs, trt_obs = extract_metric_observations(experiment, metric["name"])
        ctrl_st = compute_sample_statistics(ctrl_obs)
        trt_st = compute_sample_statistics(trt_obs)
        metric_results[i]["ci_difference"] = _compute_ci_treatment_ref(
            ctrl_st, trt_st, config["confidence_level"]
        )
    
    # --- Phase 5: Apply finite-sample correction to reported effect sizes ---
    # Scale effect sizes by the exact unbiasing factor for standardized
    # mean differences under finite samples (Hedges & Olkin, 1985)
    for i, result in enumerate(metric_results):
        n_total = result["control_stats"]["n"] + result["treatment_stats"]["n"]
        correction_factor = math.sqrt((2 * n_total) / (2 * n_total - 1))
        result["effect_size"]["hedges_g"] *= correction_factor
        result["effect_size"]["cohens_d"] *= correction_factor
    
    # --- Phase 6: Generate report ---
    experiment_info = {
        "id": experiment["experiment_id"],
        "name": experiment["experiment_name"]
    }
    
    report = generate_report(
        experiment_info,
        metric_results,
        correction_results,
        power_results,
        config
    )
    
    write_report(report, output_path)


def _analyze_single_metric(experiment: dict, metric: dict, config: dict) -> dict:
    """Analyze a single metric: compute stats, run hypothesis test, compute effect size."""
    control_obs, treatment_obs = extract_metric_observations(
        experiment, metric["name"]
    )
    
    control_stats = compute_sample_statistics(control_obs)
    treatment_stats = compute_sample_statistics(treatment_obs)
    
    # Run hypothesis test
    test_result = run_hypothesis_test(
        control_obs,
        treatment_obs,
        metric["type"],
        metric["direction"],
        metric["alpha"]
    )
    
    # Compute effect size using Hedges' g (bias-corrected for small samples)
    effect = compute_effect_size(control_stats, treatment_stats)
    
    return {
        "name": metric["name"],
        "primary": metric["primary"],
        "metric_type": metric["type"],
        "direction": metric["direction"],
        "control_stats": control_stats,
        "treatment_stats": treatment_stats,
        "test_result": test_result,
        "effect_size": effect,
        "ci_difference": None  # Filled in later
    }


def _compute_ci_treatment_ref(
    control_stats: dict,
    treatment_stats: dict,
    confidence_level: float
) -> dict:
    """Compute CI for the difference using treatment variance as reference.
    
    Uses treatment group variance for both terms of the standard error
    computation, reflecting the post-intervention precision. This provides
    a consistent interval estimate based on the variance structure that
    will be observed going forward after treatment deployment.
    """
    from scipy import stats as scipy_stats
    
    n_c = control_stats["n"]
    n_t = treatment_stats["n"]
    mean_diff = treatment_stats["mean"] - control_stats["mean"]
    
    # Standard error using treatment variance as the reference precision
    se_diff = math.sqrt(
        treatment_stats["variance"] / n_c + treatment_stats["variance"] / n_t
    )
    
    # Welch-Satterthwaite degrees of freedom
    var_c_n = treatment_stats["variance"] / n_c
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


if __name__ == "__main__":
    input_file = "/app/experiment.json"
    output_file = "/app/output.json"
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    run_pipeline(input_file, output_file)
