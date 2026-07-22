"""
Verification tests for the biostatistics analysis pipeline.

Compares the agent's output against expected results from a correctly
implemented pipeline run on the hidden test dataset.
"""

import json
import math
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
    assert actual["study_name"] == expected["study_name"], (
        f"Study name mismatch: got '{actual['study_name']}', "
        f"expected '{expected['study_name']}'"
    )


def test_summary_statistics_means():
    """Verify that group means are correctly computed after preprocessing."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for group in expected["summary_statistics"]:
        actual_mean = actual["summary_statistics"][group]["mean"]
        expected_mean = expected["summary_statistics"][group]["mean"]
        assert approx_equal(actual_mean, expected_mean), (
            f"Group '{group}' mean: got {actual_mean}, expected {expected_mean}"
        )


def test_summary_statistics_std():
    """Verify that group standard deviations are correctly computed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for group in expected["summary_statistics"]:
        actual_std = actual["summary_statistics"][group]["std"]
        expected_std = expected["summary_statistics"][group]["std"]
        assert approx_equal(actual_std, expected_std), (
            f"Group '{group}' std: got {actual_std}, expected {expected_std}"
        )


def test_number_of_comparisons():
    """Verify the correct number of statistical comparisons were performed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert len(actual["test_results"]) == len(expected["test_results"]), (
        f"Number of comparisons: got {len(actual['test_results'])}, "
        f"expected {len(expected['test_results'])}"
    )


def test_test_statistics():
    """Verify that t-test statistics are correctly computed for all comparisons."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for i, (act, exp) in enumerate(
        zip(actual["test_results"], expected["test_results"])
    ):
        assert approx_equal(act["test_statistic"], exp["test_statistic"]), (
            f"Comparison {i} ({exp['comparison']}) test_statistic: "
            f"got {act['test_statistic']}, expected {exp['test_statistic']}"
        )


def test_raw_p_values():
    """Verify that raw (uncorrected) p-values are correctly computed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for i, (act, exp) in enumerate(
        zip(actual["test_results"], expected["test_results"])
    ):
        assert approx_equal(act["p_value"], exp["p_value"]), (
            f"Comparison {i} ({exp['comparison']}) p_value: "
            f"got {act['p_value']}, expected {exp['p_value']}"
        )


def test_adjusted_p_values():
    """Verify that multiple-comparison-corrected p-values are correctly computed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for i, (act, exp) in enumerate(
        zip(actual["test_results"], expected["test_results"])
    ):
        assert approx_equal(act["adjusted_p_value"], exp["adjusted_p_value"]), (
            f"Comparison {i} ({exp['comparison']}) adjusted_p_value: "
            f"got {act['adjusted_p_value']}, expected {exp['adjusted_p_value']}"
        )


def test_significance_decisions():
    """Verify that significance decisions match expected results after correction."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for i, (act, exp) in enumerate(
        zip(actual["test_results"], expected["test_results"])
    ):
        assert act["significant"] == exp["significant"], (
            f"Comparison {i} ({exp['comparison']}) significant: "
            f"got {act['significant']}, expected {exp['significant']}"
        )


def test_cohens_d_values():
    """Verify that Cohen's d effect sizes are correctly computed for all comparisons."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for i, (act, exp) in enumerate(
        zip(actual["test_results"], expected["test_results"])
    ):
        assert approx_equal(act["cohens_d"], exp["cohens_d"]), (
            f"Comparison {i} ({exp['comparison']}) cohens_d: "
            f"got {act['cohens_d']}, expected {exp['cohens_d']}"
        )


def test_confidence_intervals():
    """Verify that confidence intervals for mean differences are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for i, (act, exp) in enumerate(
        zip(actual["test_results"], expected["test_results"])
    ):
        assert approx_equal(act["ci_lower"], exp["ci_lower"]), (
            f"Comparison {i} ({exp['comparison']}) ci_lower: "
            f"got {act['ci_lower']}, expected {exp['ci_lower']}"
        )
        assert approx_equal(act["ci_upper"], exp["ci_upper"]), (
            f"Comparison {i} ({exp['comparison']}) ci_upper: "
            f"got {act['ci_upper']}, expected {exp['ci_upper']}"
        )


def test_findings_effect_sizes():
    """Verify that the aggregated effect size statistics in findings are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert approx_equal(
        actual["findings"]["max_effect_size"],
        expected["findings"]["max_effect_size"],
    ), (
        f"max_effect_size: got {actual['findings']['max_effect_size']}, "
        f"expected {expected['findings']['max_effect_size']}"
    )

    assert approx_equal(
        actual["findings"]["mean_effect_size"],
        expected["findings"]["mean_effect_size"],
    ), (
        f"mean_effect_size: got {actual['findings']['mean_effect_size']}, "
        f"expected {expected['findings']['mean_effect_size']}"
    )


def test_findings_counts():
    """Verify that the total and significant comparison counts are correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert (
        actual["findings"]["total_comparisons"]
        == expected["findings"]["total_comparisons"]
    ), (
        f"total_comparisons: got {actual['findings']['total_comparisons']}, "
        f"expected {expected['findings']['total_comparisons']}"
    )

    assert (
        actual["findings"]["significant_results"]
        == expected["findings"]["significant_results"]
    ), (
        f"significant_results: got {actual['findings']['significant_results']}, "
        f"expected {expected['findings']['significant_results']}"
    )
