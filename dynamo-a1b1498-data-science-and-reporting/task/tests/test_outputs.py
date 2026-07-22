"""
Verification tests for the survival analysis pipeline.

Compares the agent's output against expected results from a correctly
implemented pipeline run on the hidden test dataset.
"""

import json
import os

EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"


def load_json(path):
    """Load and parse a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4, abs_tol=1e-6):
    """Check if two floating point numbers are approximately equal."""
    if a == b:
        return True
    if a is None or b is None:
        return a == b
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def test_output_file_exists():
    """Verify that the pipeline produced an output file at the expected path."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH), (
        f"Output file not found at {ACTUAL_OUTPUT_PATH}"
    )


def test_output_is_valid_json():
    """Verify that the output file contains valid JSON."""
    try:
        load_json(ACTUAL_OUTPUT_PATH)
    except (json.JSONDecodeError, Exception) as e:
        assert False, f"Output is not valid JSON: {e}"


def test_study_name():
    """Verify the study name matches the expected value."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["study_name"] == expected["study_name"]


def test_patient_counts():
    """Verify total patient and event counts are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["n_patients"] == expected["n_patients"]
    assert actual["n_events"] == expected["n_events"]


def test_km_survival_values_standard():
    """Verify Kaplan-Meier survival estimates for the standard group are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    act_curve = actual["kaplan_meier"]["standard"]["survival_curve"]
    exp_curve = expected["kaplan_meier"]["standard"]["survival_curve"]

    assert len(act_curve) == len(exp_curve), (
        f"Standard KM curve length: got {len(act_curve)}, expected {len(exp_curve)}"
    )

    for i, (act, exp) in enumerate(zip(act_curve, exp_curve)):
        assert approx_equal(act["survival"], exp["survival"]), (
            f"Standard KM at t={exp['time']}: got {act['survival']}, "
            f"expected {exp['survival']}"
        )


def test_km_survival_values_intensive():
    """Verify Kaplan-Meier survival estimates for the intensive group are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    act_curve = actual["kaplan_meier"]["intensive"]["survival_curve"]
    exp_curve = expected["kaplan_meier"]["intensive"]["survival_curve"]

    assert len(act_curve) == len(exp_curve), (
        f"Intensive KM curve length: got {len(act_curve)}, expected {len(exp_curve)}"
    )

    for i, (act, exp) in enumerate(zip(act_curve, exp_curve)):
        assert approx_equal(act["survival"], exp["survival"]), (
            f"Intensive KM at t={exp['time']}: got {act['survival']}, "
            f"expected {exp['survival']}"
        )


def test_km_median_survival():
    """Verify median survival time estimates for each group."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for group in ["standard", "intensive"]:
        act_med = actual["kaplan_meier"][group]["median_survival"]
        exp_med = expected["kaplan_meier"][group]["median_survival"]
        assert act_med == exp_med, (
            f"{group} median survival: got {act_med}, expected {exp_med}"
        )


def test_log_rank_chi_square():
    """Verify the log-rank chi-square test statistic is correctly computed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    act_lr = actual["log_rank_tests"][0]
    exp_lr = expected["log_rank_tests"][0]

    assert approx_equal(act_lr["chi_square"], exp_lr["chi_square"]), (
        f"Log-rank chi2: got {act_lr['chi_square']}, expected {exp_lr['chi_square']}"
    )


def test_log_rank_p_value():
    """Verify the log-rank test p-value is correctly computed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    act_lr = actual["log_rank_tests"][0]
    exp_lr = expected["log_rank_tests"][0]

    assert approx_equal(act_lr["p_value"], exp_lr["p_value"]), (
        f"Log-rank p-value: got {act_lr['p_value']}, expected {exp_lr['p_value']}"
    )


def test_log_rank_expected_events():
    """Verify expected event counts under the null hypothesis are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    act_lr = actual["log_rank_tests"][0]
    exp_lr = expected["log_rank_tests"][0]

    assert approx_equal(act_lr["expected_events_a"], exp_lr["expected_events_a"]), (
        f"Expected events A: got {act_lr['expected_events_a']}, "
        f"expected {exp_lr['expected_events_a']}"
    )
    assert approx_equal(act_lr["expected_events_b"], exp_lr["expected_events_b"]), (
        f"Expected events B: got {act_lr['expected_events_b']}, "
        f"expected {exp_lr['expected_events_b']}"
    )


def test_cox_concordance():
    """Verify the Cox model concordance index is correctly computed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert approx_equal(
        actual["cox_model"]["concordance_index"],
        expected["cox_model"]["concordance_index"],
    ), (
        f"Concordance: got {actual['cox_model']['concordance_index']}, "
        f"expected {expected['cox_model']['concordance_index']}"
    )


def test_cox_hazard_ratios():
    """Verify Cox model hazard ratio estimates are correct for all covariates."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    act_hrs = {hr["feature"]: hr for hr in actual["cox_model"]["hazard_ratios"]}
    exp_hrs = {hr["feature"]: hr for hr in expected["cox_model"]["hazard_ratios"]}

    for feature in exp_hrs:
        assert feature in act_hrs, f"Missing hazard ratio for '{feature}'"
        assert approx_equal(
            act_hrs[feature]["coefficient"], exp_hrs[feature]["coefficient"]
        ), (
            f"Cox coef '{feature}': got {act_hrs[feature]['coefficient']}, "
            f"expected {exp_hrs[feature]['coefficient']}"
        )


def test_summary_concordance():
    """Verify the summary concordance index matches the Cox model value."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert approx_equal(
        actual["summary"]["concordance_index"],
        expected["summary"]["concordance_index"],
    ), (
        f"Summary concordance: got {actual['summary']['concordance_index']}, "
        f"expected {expected['summary']['concordance_index']}"
    )
