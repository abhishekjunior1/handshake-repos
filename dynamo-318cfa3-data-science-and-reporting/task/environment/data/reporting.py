"""Report generation for A/B test experiment analysis.

Produces a structured JSON report containing all analysis results
including statistics, hypothesis tests, corrections, effect sizes,
confidence intervals, and power analysis.
"""

import json
from typing import Any


def generate_report(
    experiment_info: dict[str, str],
    metric_results: list[dict[str, Any]],
    correction_results: dict[str, Any],
    power_results: dict[str, Any],
    analysis_config: dict[str, Any]
) -> dict[str, Any]:
    """Generate the complete experiment analysis report.
    
    Parameters
    ----------
    experiment_info : basic experiment identifiers
    metric_results : per-metric analysis results (stats, tests, CIs, effects)
    correction_results : multiple testing correction output
    power_results : power analysis and MDE results
    analysis_config : configuration parameters used
    """
    report = {
        "experiment": experiment_info,
        "analysis_config": _format_config(analysis_config),
        "metrics": _format_metric_results(metric_results, correction_results),
        "multiple_testing": _format_corrections(correction_results),
        "power_analysis": _format_power(power_results),
        "summary": _generate_summary(metric_results, correction_results, power_results)
    }
    
    return report


def _format_config(config: dict) -> dict[str, Any]:
    """Format the analysis configuration for the report."""
    return {
        "confidence_level": config["confidence_level"],
        "correction_method": config["correction_method"],
        "power_target": config["power_target"],
        "mde_requested": config.get("minimum_detectable_effect")
    }


def _format_metric_results(
    metric_results: list[dict],
    correction_results: dict
) -> list[dict[str, Any]]:
    """Format per-metric results with corrected p-values."""
    formatted = []
    adjusted_p_values = correction_results.get("adjusted_p_values", [])
    rejections = correction_results.get("rejections", [])
    
    for i, result in enumerate(metric_results):
        entry = {
            "name": result["name"],
            "primary": result["primary"],
            "control": {
                "n": result["control_stats"]["n"],
                "mean": round(result["control_stats"]["mean"], 8),
                "std_dev": round(result["control_stats"]["std_dev"], 8),
                "se": round(result["control_stats"]["standard_error"], 8)
            },
            "treatment": {
                "n": result["treatment_stats"]["n"],
                "mean": round(result["treatment_stats"]["mean"], 8),
                "std_dev": round(result["treatment_stats"]["std_dev"], 8),
                "se": round(result["treatment_stats"]["standard_error"], 8)
            },
            "hypothesis_test": {
                "test_type": result["test_result"]["test_type"],
                "statistic": result["test_result"]["test_statistic"],
                "p_value_raw": result["test_result"]["p_value"],
                "p_value_adjusted": adjusted_p_values[i] if i < len(adjusted_p_values) else result["test_result"]["p_value"],
                "reject_null_corrected": bool(rejections[i]) if i < len(rejections) else bool(result["test_result"]["reject_null"]),
                "degrees_of_freedom": result["test_result"]["degrees_of_freedom"]
            },
            "effect_size": {
                "hedges_g": round(result["effect_size"]["hedges_g"], 8),
                "cohens_d": round(result["effect_size"]["cohens_d"], 8),
                "mean_difference": round(result["effect_size"]["mean_difference"], 8)
            },
            "confidence_interval": {
                "ci_lower": round(result["ci_difference"]["ci_lower"], 8),
                "ci_upper": round(result["ci_difference"]["ci_upper"], 8),
                "se_difference": round(result["ci_difference"]["se_difference"], 8),
                "margin_of_error": round(result["ci_difference"]["margin_of_error"], 8)
            }
        }
        formatted.append(entry)
    
    return formatted


def _format_corrections(correction_results: dict) -> dict[str, Any]:
    """Format the multiple testing correction results."""
    return {
        "method": correction_results["method"],
        "num_comparisons": correction_results["num_comparisons"],
        "adjusted_p_values": correction_results["adjusted_p_values"],
        "rejections": correction_results["rejections"]
    }


def _format_power(power_results: dict) -> dict[str, Any]:
    """Format power analysis results."""
    return {
        "achieved_power": power_results["power"]["achieved_power"],
        "noncentrality_parameter": power_results["power"]["noncentrality_parameter"],
        "mde": {
            "absolute": power_results["mde"]["mde_absolute"],
            "relative": power_results["mde"]["mde_relative"],
            "standard_error": power_results["mde"]["standard_error"]
        },
        "sample_size_recommendation": power_results.get("sample_size_rec", {})
    }


def _generate_summary(
    metric_results: list[dict],
    correction_results: dict,
    power_results: dict
) -> dict[str, Any]:
    """Generate a summary of the experiment analysis."""
    rejections = correction_results.get("rejections", [])
    significant_count = sum(1 for r in rejections if r)
    total_metrics = len(metric_results)
    
    primary_metrics = [m for m in metric_results if m["primary"]]
    primary_significant = any(
        rejections[i] for i, m in enumerate(metric_results)
        if m["primary"] and i < len(rejections)
    )
    
    adequately_powered = bool(power_results["power"]["achieved_power"] >= 0.8)
    
    return {
        "total_metrics_tested": total_metrics,
        "significant_after_correction": significant_count,
        "primary_metric_significant": bool(primary_significant),
        "adequately_powered": adequately_powered,
        "achieved_power": power_results["power"]["achieved_power"],
        "recommendation": _get_recommendation(
            primary_significant, adequately_powered, significant_count, total_metrics
        )
    }


def _get_recommendation(
    primary_sig: bool,
    powered: bool,
    sig_count: int,
    total: int
) -> str:
    """Generate a recommendation based on results."""
    if primary_sig and powered:
        return "SHIP: Primary metric shows significant improvement with adequate power."
    elif primary_sig and not powered:
        return "CAUTIOUS_SHIP: Primary metric significant but study may be underpowered."
    elif not primary_sig and powered:
        return "NO_EFFECT: Adequately powered study found no significant primary effect."
    else:
        return "INCONCLUSIVE: Underpowered study with no significant primary effect. Consider larger sample."


def write_report(report: dict, filepath: str) -> None:
    """Write the report to a JSON file."""
    with open(filepath, 'w') as f:
        json.dump(report, f, indent=2, default=_json_serializer)


def _json_serializer(obj):
    """Handle non-standard types in JSON serialization."""
    if isinstance(obj, bool):
        return bool(obj)
    if hasattr(obj, 'item'):  # numpy scalars
        return obj.item()
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
