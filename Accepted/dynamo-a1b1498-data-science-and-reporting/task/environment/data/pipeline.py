"""
Clinical Survival Analysis Pipeline

Processes time-to-event patient data through a multi-stage analysis:
1. Load and validate patient cohort data
2. Preprocess (censoring classification, covariate standardization)
3. Estimate survival curves via Kaplan-Meier
4. Compare groups via log-rank test
5. Fit Cox proportional hazards model
6. Generate structured output report with concordance metrics

Usage: python3 /app/pipeline.py
Reads: /app/cohort_data.json
Writes: /app/output.json
"""

import json
import sys
import os

from data_loader import load_cohort_data, validate_cohort_schema
from preprocessor import (
    classify_events,
    standardize_covariates,
    build_time_table,
)
from kaplan_meier import (
    compute_km_estimate,
    compute_km_confidence_intervals,
    compute_median_survival,
)
from log_rank import (
    compute_log_rank_statistic,
    compute_expected_events,
    log_rank_p_value,
)
from cox_model import (
    fit_cox_model,
    compute_concordance_index,
    compute_hazard_ratios,
)
from report_generator import (
    build_survival_report,
    format_km_results,
    format_cox_results,
)


def run_pipeline(input_path, output_path):
    """Execute the full survival analysis pipeline."""

    # Stage 1: Load and validate
    raw_data = load_cohort_data(input_path)
    validation_result = validate_cohort_schema(raw_data)
    if not validation_result["valid"]:
        sys.exit(f"Schema validation failed: {validation_result['errors']}")

    study_config = raw_data["study_config"]
    patients = raw_data["patients"]
    analysis_params = raw_data["analysis_params"]

    # Stage 2: Preprocess
    group_field = study_config["group_field"]
    time_field = study_config["time_field"]
    event_field = study_config["event_field"]
    covariate_fields = study_config.get("covariates", [])

    classified = classify_events(patients, time_field, event_field)

    # Build time tables per group
    groups = {}
    for patient in classified:
        g = patient[group_field]
        if g not in groups:
            groups[g] = []
        groups[g].append(patient)

    time_tables = {}
    for group_name, group_patients in groups.items():
        time_tables[group_name] = build_time_table(
            group_patients, time_field, event_field
        )

    # Standardize covariates for Cox model
    covariate_data = standardize_covariates(
        classified, covariate_fields
    )

    # Stage 3: Kaplan-Meier estimation per group
    km_results = {}
    for group_name, tt in time_tables.items():
        km_curve = compute_km_estimate(tt)
        ci = compute_km_confidence_intervals(
            km_curve,
            confidence_level=analysis_params.get("confidence_level", 0.95),
        )
        median = compute_median_survival(km_curve)
        km_results[group_name] = {
            "curve": km_curve,
            "confidence_intervals": ci,
            "median_survival": median,
        }

    # Stage 4: Log-rank test (pairwise group comparisons)
    group_names = sorted(groups.keys())
    log_rank_results = []

    comparisons = study_config.get("comparisons", [])
    if not comparisons:
        # Default: all pairwise
        for i in range(len(group_names)):
            for j in range(i + 1, len(group_names)):
                comparisons.append(
                    {"group_a": group_names[i], "group_b": group_names[j]}
                )

    for comp in comparisons:
        ga = comp["group_a"]
        gb = comp["group_b"]
        tt_a = time_tables[ga]
        tt_b = time_tables[gb]

        chi_sq, p_value = compute_log_rank_statistic(tt_a, tt_b)
        expected = compute_expected_events(tt_a, tt_b)

        log_rank_results.append(
            {
                "comparison": f"{ga}_vs_{gb}",
                "group_a": ga,
                "group_b": gb,
                "chi_square": chi_sq,
                "p_value": p_value,
                "expected_events_a": expected["group_a"],
                "expected_events_b": expected["group_b"],
                "observed_events_a": sum(
                    t["events"] for t in tt_a
                ),
                "observed_events_b": sum(
                    t["events"] for t in tt_b
                ),
            }
        )

    # Stage 5: Cox proportional hazards model
    alpha = analysis_params.get("alpha", 0.05)
    cox_result = fit_cox_model(
        classified,
        time_field,
        event_field,
        covariate_fields + [group_field],
        max_iter=analysis_params.get("cox_max_iter", 100),
        tol=analysis_params.get("cox_tol", 1e-9),
    )

    concordance = compute_concordance_index(
        classified, time_field, event_field, cox_result["coefficients"],
        covariate_fields + [group_field]
    )

    hazard_ratios = compute_hazard_ratios(
        cox_result["coefficients"],
        cox_result["standard_errors"],
        confidence_level=analysis_params.get("confidence_level", 0.95),
    )

    # Stage 6: Generate report
    km_formatted = format_km_results(km_results)
    cox_formatted = format_cox_results(cox_result, hazard_ratios, concordance)

    report = build_survival_report(
        study_name=study_config["study_name"],
        km_results=km_formatted,
        log_rank_results=log_rank_results,
        cox_results=cox_formatted,
        analysis_params=analysis_params,
        n_patients=len(classified),
        n_events=sum(1 for p in classified if p["_event_observed"]),
    )

    # Write output
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


if __name__ == "__main__":
    input_file = "/app/cohort_data.json"
    output_file = "/app/output.json"

    if not os.path.exists(input_file):
        sys.exit(f"Input file not found: {input_file}")

    report = run_pipeline(input_file, output_file)
    print(f"Analysis complete. Results written to {output_file}")
    print(f"Study: {report['study_name']}")
    print(f"Patients: {report['n_patients']}, Events: {report['n_events']}")
