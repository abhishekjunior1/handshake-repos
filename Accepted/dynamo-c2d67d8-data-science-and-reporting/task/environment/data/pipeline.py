"""
Clinical Biostatistics Analysis Pipeline

Processes experimental datasets through a multi-stage statistical analysis:
1. Load and validate input data
2. Preprocess (outlier handling, normalization)
3. Run statistical hypothesis tests with multiple comparison correction
4. Calculate effect sizes and confidence intervals
5. Generate structured output report

Usage: python3 /app/pipeline.py
Reads: /app/study_data.json
Writes: /app/output.json
"""

import json
import sys
import os

from data_loader import load_study_data, validate_schema
from preprocessor import preprocess_groups, detect_outliers, winsorize_data
from statistical_tests import (
    run_group_comparisons,
    apply_multiple_comparison_correction,
    compute_test_statistics,
)
from effect_size import (
    compute_cohens_d,
    compute_confidence_interval,
    compute_common_language_effect,
)
from report_generator import (
    build_analysis_report,
    format_statistical_results,
    generate_summary_statistics,
)


def run_pipeline(input_path, output_path):
    """Execute the full biostatistics analysis pipeline."""

    # Stage 1: Load and validate
    raw_data = load_study_data(input_path)
    validation_result = validate_schema(raw_data)
    if not validation_result["valid"]:
        sys.exit(f"Schema validation failed: {validation_result['errors']}")

    study_config = raw_data["study_config"]
    groups = raw_data["groups"]
    analysis_params = raw_data["analysis_params"]

    # Stage 2: Preprocess
    preprocessed_groups = {}
    outlier_report = {}

    for group_name, group_data in groups.items():
        measurements = group_data["measurements"]

        # Detect outliers using IQR method
        outlier_info = detect_outliers(
            measurements,
            method=analysis_params.get("outlier_method", "iqr"),
            threshold=analysis_params.get("outlier_threshold", 1.5),
        )
        outlier_report[group_name] = outlier_info

        # Apply winsorization if configured
        if analysis_params.get("winsorize", False):
            percentile = analysis_params.get("winsorize_percentile", 5.0)
            processed = winsorize_data(measurements, percentile)
        else:
            processed = measurements[:]

        preprocessed_groups[group_name] = preprocess_groups(
            processed,
            normalize=analysis_params.get("normalize", False),
            center=analysis_params.get("center", False),
        )

    # Stage 3: Statistical tests
    alpha = analysis_params.get("alpha", 0.05)
    comparisons = study_config.get("comparisons", [])
    test_type = analysis_params.get("test_type", "welch_t")

    raw_results = []
    for comparison in comparisons:
        group_a = comparison["group_a"]
        group_b = comparison["group_b"]

        data_a = preprocessed_groups[group_a]
        data_b = preprocessed_groups[group_b]

        test_stat, p_value = compute_test_statistics(
            data_a, data_b, test_type=test_type
        )

        raw_results.append(
            {
                "comparison": f"{group_a}_vs_{group_b}",
                "group_a": group_a,
                "group_b": group_b,
                "test_statistic": test_stat,
                "p_value": p_value,
                "test_type": test_type,
            }
        )

    # Apply multiple comparison correction
    correction_method = analysis_params.get("correction_method", "holm")
    corrected_results = apply_multiple_comparison_correction(
        raw_results, method=correction_method, alpha=alpha
    )

    # Stage 4: Effect sizes
    effect_size_results = []
    for result in corrected_results:
        group_a = result["group_a"]
        group_b = result["group_b"]

        data_a = preprocessed_groups[group_a]
        data_b = preprocessed_groups[group_b]

        cohens_d = compute_cohens_d(data_a, data_b)
        ci_lower, ci_upper = compute_confidence_interval(
            data_a, data_b, confidence_level=1 - alpha
        )
        cles = compute_common_language_effect(data_a, data_b)

        effect_size_results.append(
            {
                "comparison": result["comparison"],
                "cohens_d": cohens_d,
                "ci_lower": ci_lower,
                "ci_upper": ci_upper,
                "common_language_effect": cles,
            }
        )

    # Stage 5: Generate report
    summary_stats = generate_summary_statistics(preprocessed_groups)
    formatted_results = format_statistical_results(corrected_results, effect_size_results)

    report = build_analysis_report(
        study_name=study_config["study_name"],
        summary_statistics=summary_stats,
        test_results=formatted_results,
        outlier_report=outlier_report,
        analysis_params=analysis_params,
        alpha=alpha,
    )

    # Write output
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    input_file = "/app/study_data.json"
    output_file = "/app/output.json"

    if not os.path.exists(input_file):
        sys.exit(f"Input file not found: {input_file}")

    report = run_pipeline(input_file, output_file)
    print(f"Analysis complete. Results written to {output_file}")
    print(f"Study: {report['study_name']}")
    print(f"Comparisons analyzed: {len(report['test_results'])}")
