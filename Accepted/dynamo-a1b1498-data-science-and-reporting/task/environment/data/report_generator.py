"""
Report generator module for the survival analysis pipeline.

Formats Kaplan-Meier curves, log-rank tests, and Cox model results into
a structured analysis report for JSON serialization.
"""


def format_km_results(km_results):
    """
    Format Kaplan-Meier results for each group into the report structure.

    Extracts key survival probabilities at landmark time points and
    summarizes the curve characteristics.

    Parameters
    ----------
    km_results : dict
        Dictionary mapping group names to KM results (curve, CI, median).

    Returns
    -------
    dict
        Formatted KM results per group with survival_at_landmarks,
        median_survival, and curve summary.
    """
    formatted = {}

    for group_name, results in km_results.items():
        curve = results["curve"]
        ci = results["confidence_intervals"]
        median = results["median_survival"]

        # Extract survival at event times
        survival_steps = []
        for i, entry in enumerate(curve):
            if entry["events"] > 0:
                ci_entry = ci[i] if i < len(ci) else {"lower": 0, "upper": 1}
                survival_steps.append(
                    {
                        "time": entry["time"],
                        "survival": entry["survival"],
                        "ci_lower": ci_entry["lower"],
                        "ci_upper": ci_entry["upper"],
                        "at_risk": entry["at_risk"],
                        "events": entry["events"],
                    }
                )

        # Summary statistics
        final_survival = curve[-1]["survival"] if curve else 1.0
        total_events = sum(e["events"] for e in curve)
        total_censored = sum(e["censored"] for e in curve)

        formatted[group_name] = {
            "median_survival": median,
            "final_survival": round(final_survival, 6),
            "total_events": total_events,
            "total_censored": total_censored,
            "n_patients": total_events + total_censored,
            "survival_curve": survival_steps,
        }

    return formatted


def format_cox_results(cox_result, hazard_ratios, concordance):
    """
    Format Cox model results for the report.

    Parameters
    ----------
    cox_result : dict
        Fitted Cox model output.
    hazard_ratios : list of dict
        Hazard ratio results for each covariate.
    concordance : float
        Concordance index.

    Returns
    -------
    dict
        Formatted Cox results.
    """
    return {
        "log_likelihood": cox_result["log_likelihood"],
        "n_iterations": cox_result["n_iterations"],
        "converged": cox_result["converged"],
        "concordance_index": round(concordance, 6),
        "hazard_ratios": hazard_ratios,
    }


def build_survival_report(
    study_name,
    km_results,
    log_rank_results,
    cox_results,
    analysis_params,
    n_patients,
    n_events,
):
    """
    Assemble the complete survival analysis report.

    Parameters
    ----------
    study_name : str
        Name of the study.
    km_results : dict
        Formatted Kaplan-Meier results.
    log_rank_results : list of dict
        Log-rank test results for each comparison.
    cox_results : dict
        Formatted Cox model results.
    analysis_params : dict
        Analysis parameters used.
    n_patients : int
        Total number of patients.
    n_events : int
        Total number of events observed.

    Returns
    -------
    dict
        Complete survival analysis report.
    """
    # Determine overall significance
    alpha = analysis_params.get("alpha", 0.05)
    significant_comparisons = sum(
        1 for r in log_rank_results if r["p_value"] < alpha
    )

    # Format log-rank results with rounded values
    formatted_log_rank = []
    for result in log_rank_results:
        formatted_log_rank.append(
            {
                "comparison": result["comparison"],
                "chi_square": round(result["chi_square"], 6),
                "p_value": round(result["p_value"], 6),
                "significant": result["p_value"] < alpha,
                "observed_events_a": result["observed_events_a"],
                "observed_events_b": result["observed_events_b"],
                "expected_events_a": round(result["expected_events_a"], 6),
                "expected_events_b": round(result["expected_events_b"], 6),
            }
        )

    report = {
        "study_name": study_name,
        "n_patients": n_patients,
        "n_events": n_events,
        "censoring_rate": round(1.0 - n_events / n_patients, 6) if n_patients > 0 else 0.0,
        "analysis_parameters": {
            "alpha": alpha,
            "confidence_level": analysis_params.get("confidence_level", 0.95),
        },
        "kaplan_meier": km_results,
        "log_rank_tests": formatted_log_rank,
        "cox_model": cox_results,
        "summary": {
            "total_comparisons": len(log_rank_results),
            "significant_comparisons": significant_comparisons,
            "concordance_index": cox_results["concordance_index"],
        },
    }

    return report
