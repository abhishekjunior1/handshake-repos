"""
Report generator module for the biostatistics pipeline.

Formats statistical test results, computes summary statistics, and
assembles the final structured analysis report in JSON format.
"""

import math


def generate_summary_statistics(preprocessed_groups):
    """
    Compute descriptive statistics for each group after preprocessing.

    Parameters
    ----------
    preprocessed_groups : dict
        Dictionary mapping group names to lists of preprocessed measurements.

    Returns
    -------
    dict
        Dictionary mapping group names to their summary statistics including
        mean, median, std, min, max, n, and standard error.
    """
    summary = {}

    for group_name, measurements in preprocessed_groups.items():
        n = len(measurements)
        if n == 0:
            summary[group_name] = {
                "n": 0,
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "se": 0.0,
                "skewness": 0.0,
                "kurtosis": 0.0,
            }
            continue

        mean = sum(measurements) / n
        sorted_data = sorted(measurements)

        if n % 2 == 0:
            median = (sorted_data[n // 2 - 1] + sorted_data[n // 2]) / 2.0
        else:
            median = sorted_data[n // 2]

        # Sample standard deviation (ddof=1)
        if n > 1:
            variance = sum((x - mean) ** 2 for x in measurements) / (n - 1)
            std = math.sqrt(variance)
        else:
            variance = 0.0
            std = 0.0

        se = std / math.sqrt(n) if n > 0 else 0.0

        # Skewness (Fisher's definition)
        skewness = 0.0
        if n > 2 and std > 0:
            m3 = sum((x - mean) ** 3 for x in measurements) / n
            skewness = (n * m3) / ((n - 1) * (n - 2) * (std ** 3)) * n
            # Adjusted formula
            skewness = (
                (n / ((n - 1) * (n - 2)))
                * sum(((x - mean) / std) ** 3 for x in measurements)
            )

        # Excess kurtosis
        kurtosis = 0.0
        if n > 3 and std > 0:
            m4 = sum((x - mean) ** 4 for x in measurements) / n
            kurtosis = (n * (n + 1) * m4) / (
                (n - 1) * (n - 2) * (n - 3) * variance ** 2
            ) - (3 * (n - 1) ** 2) / ((n - 2) * (n - 3))

        summary[group_name] = {
            "n": n,
            "mean": round(mean, 10),
            "median": round(median, 10),
            "std": round(std, 10),
            "min": round(min(measurements), 10),
            "max": round(max(measurements), 10),
            "se": round(se, 10),
            "skewness": round(skewness, 6),
            "kurtosis": round(kurtosis, 6),
        }

    return summary


def format_statistical_results(corrected_results, effect_size_results):
    """
    Merge statistical test results with effect size calculations into
    a unified format for the final report.

    Parameters
    ----------
    corrected_results : list of dict
        Results from hypothesis testing with multiple comparison correction.
    effect_size_results : list of dict
        Effect size calculations for each comparison.

    Returns
    -------
    list of dict
        Combined results with test statistics, p-values, significance,
        and effect sizes.
    """
    formatted = []

    # Create lookup by comparison name
    effect_lookup = {}
    for es in effect_size_results:
        effect_lookup[es["comparison"]] = es

    for result in corrected_results:
        comparison_name = result["comparison"]
        entry = {
            "comparison": comparison_name,
            "test_type": result["test_type"],
            "test_statistic": round(result["test_statistic"], 6),
            "p_value": round(result["p_value"], 6),
            "adjusted_p_value": round(result["adjusted_p_value"], 6),
            "significant": result["significant"],
            "correction_method": result["correction_method"],
        }

        if comparison_name in effect_lookup:
            es = effect_lookup[comparison_name]
            entry["cohens_d"] = round(es["cohens_d"], 6)
            entry["ci_lower"] = round(es["ci_lower"], 6)
            entry["ci_upper"] = round(es["ci_upper"], 6)
            entry["common_language_effect"] = round(
                es["common_language_effect"], 6
            )

        formatted.append(entry)

    return formatted


def build_analysis_report(
    study_name,
    summary_statistics,
    test_results,
    outlier_report,
    analysis_params,
    alpha,
):
    """
    Assemble the complete analysis report from all pipeline components.

    Parameters
    ----------
    study_name : str
        Name of the study being analyzed.
    summary_statistics : dict
        Descriptive statistics for each group.
    test_results : list of dict
        Formatted statistical test results.
    outlier_report : dict
        Outlier detection results for each group.
    analysis_params : dict
        Parameters used in the analysis.
    alpha : float
        Significance threshold used.

    Returns
    -------
    dict
        Complete structured analysis report ready for JSON serialization.
    """
    # Compute overall findings
    n_significant = sum(1 for r in test_results if r["significant"])
    n_tests = len(test_results)

    # Compute the range of effect sizes
    effect_sizes = [
        abs(r["cohens_d"]) for r in test_results if "cohens_d" in r
    ]
    max_effect = max(effect_sizes) if effect_sizes else 0.0
    min_effect = min(effect_sizes) if effect_sizes else 0.0
    mean_effect = (
        sum(effect_sizes) / len(effect_sizes) if effect_sizes else 0.0
    )

    # Classify effect sizes per Cohen's conventions
    effect_classifications = []
    for r in test_results:
        if "cohens_d" in r:
            d = abs(r["cohens_d"])
            if d < 0.2:
                classification = "negligible"
            elif d < 0.5:
                classification = "small"
            elif d < 0.8:
                classification = "medium"
            else:
                classification = "large"
            effect_classifications.append(
                {"comparison": r["comparison"], "magnitude": classification}
            )

    # Count total outliers across all groups
    total_outliers = sum(
        info["outlier_count"] for info in outlier_report.values()
    )

    report = {
        "study_name": study_name,
        "analysis_parameters": {
            "alpha": alpha,
            "test_type": analysis_params.get("test_type", "welch_t"),
            "correction_method": analysis_params.get("correction_method", "holm"),
            "winsorize": analysis_params.get("winsorize", False),
            "winsorize_percentile": analysis_params.get("winsorize_percentile", 5.0),
            "outlier_method": analysis_params.get("outlier_method", "iqr"),
            "outlier_threshold": analysis_params.get("outlier_threshold", 1.5),
        },
        "summary_statistics": summary_statistics,
        "outlier_report": outlier_report,
        "test_results": test_results,
        "findings": {
            "total_comparisons": n_tests,
            "significant_results": n_significant,
            "non_significant_results": n_tests - n_significant,
            "max_effect_size": round(max_effect, 6),
            "min_effect_size": round(min_effect, 6),
            "mean_effect_size": round(mean_effect, 6),
            "effect_classifications": effect_classifications,
            "total_outliers_detected": total_outliers,
        },
    }

    return report


def interpret_significance(p_value, alpha, effect_size):
    """
    Provide a categorical interpretation of a statistical result based on
    both significance and effect size.

    Parameters
    ----------
    p_value : float
        The (adjusted) p-value.
    alpha : float
        Significance threshold.
    effect_size : float
        Absolute Cohen's d value.

    Returns
    -------
    str
        One of: 'strong_evidence', 'moderate_evidence', 'weak_evidence', 'no_evidence'
    """
    if p_value >= alpha:
        return "no_evidence"

    if effect_size >= 0.8:
        return "strong_evidence"
    elif effect_size >= 0.5:
        return "moderate_evidence"
    else:
        return "weak_evidence"
