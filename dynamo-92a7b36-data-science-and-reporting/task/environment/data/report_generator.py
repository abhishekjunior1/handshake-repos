"""Report generation module for meta-analysis results.

Structures analysis results into a comprehensive JSON output format
including overall estimates, subgroup analyses, and diagnostic tests.
"""

import json
from typing import Any

from heterogeneity import estimate_heterogeneity, compute_weights, compute_fixed_effect_estimate
from random_effects import (
    run_random_effects_analysis,
    compute_random_effects_weights,
    compute_pooled_estimate,
    compute_confidence_interval,
    compute_prediction_interval,
)
from egger_test import run_egger_test


def generate_subgroup_analysis(
    effects: list[float],
    std_errors: list[float],
    labels: list[str],
    subgroups: list[str],
    unique_subgroups: list[str],
    overall_tau_squared: float,
) -> list[dict[str, Any]]:
    """Run meta-analysis separately for each subgroup.

    Each subgroup analysis uses the common between-study variance
    estimated from the full dataset to maintain consistency across
    subgroups, particularly when individual subgroups have few studies.

    Args:
        effects: All study effect sizes.
        std_errors: All standard errors.
        labels: All study labels.
        subgroups: Subgroup assignment for each study.
        unique_subgroups: Sorted list of unique subgroup names.
        overall_tau_squared: Between-study variance from overall analysis.

    Returns:
        List of dictionaries, each containing subgroup-specific results.
    """
    subgroup_results = []

    for sg in unique_subgroups:
        sg_effects = []
        sg_ses = []
        sg_labels = []

        for i, group in enumerate(subgroups):
            if group == sg:
                sg_effects.append(effects[i])
                sg_ses.append(std_errors[i])
                sg_labels.append(labels[i])

        k = len(sg_effects)

        if k < 2:
            subgroup_results.append({
                "subgroup": sg,
                "num_studies": k,
                "analysis": None,
                "note": "Insufficient studies for meta-analysis",
            })
            continue

        # Use overall tau² for subgroup weights (common heterogeneity assumption)
        re_weights = compute_random_effects_weights(sg_ses, overall_tau_squared)
        pooled, se_pooled = compute_pooled_estimate(sg_effects, re_weights)
        ci_lower, ci_upper = compute_confidence_interval(pooled, se_pooled)
        pi_lower, pi_upper = compute_prediction_interval(
            pooled, se_pooled, overall_tau_squared, k
        )

        # Fixed-effect within subgroup
        fe_weights = compute_weights(sg_ses)
        fe_pooled = compute_fixed_effect_estimate(sg_effects, fe_weights)

        # Subgroup heterogeneity
        sg_het = estimate_heterogeneity(sg_effects, sg_ses)

        subgroup_results.append({
            "subgroup": sg,
            "num_studies": k,
            "studies": sg_labels,
            "analysis": {
                "random_effects": {
                    "pooled_estimate": round(pooled, 6),
                    "std_error": round(se_pooled, 6),
                    "ci_lower": round(ci_lower, 6),
                    "ci_upper": round(ci_upper, 6),
                    "prediction_interval_lower": round(pi_lower, 6),
                    "prediction_interval_upper": round(pi_upper, 6),
                    "num_studies": k,
                },
                "fixed_effect": {
                    "pooled_estimate": round(fe_pooled, 6),
                },
                "heterogeneity": sg_het,
            },
        })

    return subgroup_results


def compute_between_subgroup_q(
    subgroup_results: list[dict[str, Any]],
    overall_pooled: float,
) -> dict[str, Any]:
    """Compute between-subgroup heterogeneity Q statistic.

    Tests whether subgroup pooled estimates differ significantly from
    each other. Uses inverse-variance weights based on each subgroup's
    pooled standard error.

    Args:
        subgroup_results: List of subgroup analysis results.
        overall_pooled: Overall random-effects pooled estimate.

    Returns:
        Dictionary with Q_between, df, and p-value.
    """
    from heterogeneity import chi2_survival

    q_between = 0.0
    valid_subgroups = 0

    for sg in subgroup_results:
        if sg["analysis"] is None:
            continue
        sg_pooled = sg["analysis"]["random_effects"]["pooled_estimate"]
        sg_se = sg["analysis"]["random_effects"]["std_error"]

        if sg_se > 0:
            weight = 1.0 / (sg_se * sg_se)
            q_between += weight * (sg_pooled - overall_pooled) ** 2
            valid_subgroups += 1

    df = valid_subgroups - 1
    p_value = chi2_survival(q_between, df) if df > 0 and q_between > 0 else 1.0

    return {
        "Q_between": round(q_between, 6),
        "df": df,
        "p_value": round(p_value, 6),
    }


def compute_summary_statistics(
    effects: list[float], std_errors: list[float]
) -> dict[str, Any]:
    """Compute descriptive statistics for the input data.

    Args:
        effects: List of study effect sizes.
        std_errors: List of standard errors.

    Returns:
        Dictionary with min, max, mean, and median of effects and SEs.
    """
    sorted_effects = sorted(effects)
    sorted_ses = sorted(std_errors)
    n = len(effects)

    def median(vals: list[float]) -> float:
        m = len(vals)
        if m % 2 == 0:
            return (vals[m // 2 - 1] + vals[m // 2]) / 2.0
        return vals[m // 2]

    return {
        "effects": {
            "min": round(min(effects), 6),
            "max": round(max(effects), 6),
            "mean": round(sum(effects) / n, 6),
            "median": round(median(sorted_effects), 6),
        },
        "std_errors": {
            "min": round(min(std_errors), 6),
            "max": round(max(std_errors), 6),
            "mean": round(sum(std_errors) / n, 6),
            "median": round(median(sorted_ses), 6),
        },
    }


def generate_report(data: dict[str, Any]) -> dict[str, Any]:
    """Generate the complete meta-analysis report.

    Runs overall analysis, subgroup analyses, publication bias test,
    and assembles comprehensive structured output.

    Args:
        data: Parsed study data from data_loader.

    Returns:
        Complete analysis report as nested dictionary.
    """
    effects = data["effects"]
    std_errors = data["std_errors"]
    labels = data["labels"]
    subgroups = data["subgroups"]
    unique_subgroups = data["unique_subgroups"]

    # Overall analysis
    overall = run_random_effects_analysis(effects, std_errors)
    overall_tau_sq = overall["heterogeneity"]["tau_squared"]
    overall_pooled = overall["random_effects"]["pooled_estimate"]

    # Publication bias
    egger = run_egger_test(effects, std_errors)

    # Subgroup analyses using overall tau²
    subgroup_results = generate_subgroup_analysis(
        effects, std_errors, labels, subgroups, unique_subgroups,
        overall_tau_sq,
    )

    # Between-subgroup heterogeneity
    between_q = compute_between_subgroup_q(subgroup_results, overall_pooled)

    summary_stats = compute_summary_statistics(effects, std_errors)

    report = {
        "analysis_name": data["analysis_name"],
        "effect_measure": data["effect_measure"],
        "num_studies": data["num_studies"],
        "summary_statistics": summary_stats,
        "overall_analysis": overall,
        "publication_bias": egger,
        "subgroup_analyses": subgroup_results,
        "between_subgroup_heterogeneity": between_q,
    }

    return report


def write_report(report: dict[str, Any], output_path: str) -> None:
    """Write the analysis report to a JSON file.

    Args:
        report: Complete analysis report dictionary.
        output_path: File path for output JSON.
    """
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)
