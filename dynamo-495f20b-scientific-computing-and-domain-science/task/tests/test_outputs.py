"""
Verification tests for the Bayesian hierarchical model fitting pipeline.
Tests run against hidden observation data to verify correct shrinkage
estimation, credible interval computation, and model comparison criteria.
"""

import json
import subprocess
import shutil
import os
import math

import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"
HIDDEN_DATA_PATH = "/tests/hidden_observations.json"


@pytest.fixture(autouse=True)
def run_pipeline():
    """Copy hidden data and run the pipeline before tests execute."""
    shutil.copy(HIDDEN_DATA_PATH, "/app/observations.json")
    result = subprocess.run(
        ["python3", "/app/pipeline.py", "/app/observations.json", "/app/output.json"],
        cwd="/app",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"


def load_json(path):
    """Load a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produces an output.json file."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH), "output.json not produced"


def test_shrinkage_factors():
    """Verify shrinkage factors are computed correctly for each group.

    The shrinkage factor B_j = sigma²_w / ((n_j-3)*tau² + sigma²_w)
    determines how much each group mean is pulled toward the grand mean.
    With tau² >> sigma²_w, shrinkage should be minimal (B close to 0).
    Incorrect variance passed to the shrinkage computation produces
    dramatically wrong B values.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for act, exp in zip(actual["group_estimates"], expected["group_estimates"]):
        assert act["group_id"] == exp["group_id"]
        assert math.isclose(act["shrinkage_factor"], exp["shrinkage_factor"], rel_tol=1e-4), (
            f"Group {act['group_id']}: shrinkage_factor "
            f"got {act['shrinkage_factor']}, expected {exp['shrinkage_factor']}"
        )


def test_shrunken_means():
    """Verify posterior shrunken means are correct for each group.

    The shrunken mean theta_j = grand_mean + (1-B_j)*(y_bar_j - grand_mean).
    Incorrect shrinkage factors propagate into wrong posterior means,
    which in turn affect credible intervals and model diagnostics.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for act, exp in zip(actual["group_estimates"], expected["group_estimates"]):
        assert math.isclose(act["shrunken_mean"], exp["shrunken_mean"], rel_tol=1e-4), (
            f"Group {act['group_id']}: shrunken_mean "
            f"got {act['shrunken_mean']}, expected {exp['shrunken_mean']}"
        )


def test_credible_intervals():
    """Verify posterior credible intervals have correct width and bounds.

    Intervals depend on both the shrunken mean and the posterior variance,
    which in turn depends on the shrinkage factor. Incorrect shrinkage
    produces intervals that are either too wide or too narrow.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    for act, exp in zip(actual["group_estimates"], expected["group_estimates"]):
        assert math.isclose(act["ci_lower"], exp["ci_lower"], rel_tol=1e-3), (
            f"Group {act['group_id']}: ci_lower "
            f"got {act['ci_lower']}, expected {exp['ci_lower']}"
        )
        assert math.isclose(act["ci_upper"], exp["ci_upper"], rel_tol=1e-3), (
            f"Group {act['group_id']}: ci_upper "
            f"got {act['ci_upper']}, expected {exp['ci_upper']}"
        )


def test_dic_value():
    """Verify the Deviance Information Criterion is computed correctly.

    DIC = deviance_at_mean + 2*p_D where p_D is the effective number
    of parameters from the shrinkage model. Using the wrong penalty
    (e.g., number of groups instead of effective parameters) produces
    incorrect model comparison values.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert math.isclose(
        actual["model_comparison"]["dic"],
        expected["model_comparison"]["dic"],
        rel_tol=1e-3
    ), (
        f"DIC: got {actual['model_comparison']['dic']}, "
        f"expected {expected['model_comparison']['dic']}"
    )


def test_effective_parameters():
    """Verify the effective parameter count used in DIC computation.

    The effective parameters (p_D) should reflect the actual model
    complexity from shrinkage: p_D = sum(1-B_j). With strong shrinkage,
    p_D < k (number of groups). Using k directly instead of p_D
    overestimates model complexity.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert math.isclose(
        actual["model_comparison"]["effective_params_dic"],
        expected["model_comparison"]["effective_params_dic"],
        rel_tol=1e-3
    ), (
        f"Effective params (DIC): got {actual['model_comparison']['effective_params_dic']}, "
        f"expected {expected['model_comparison']['effective_params_dic']}"
    )


def test_variance_components():
    """Verify within-group and between-group variance estimates.

    The variance decomposition should correctly identify the within-group
    pooled variance and the between-group heterogeneity. These are inputs
    to the shrinkage computation and must be estimated correctly.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert math.isclose(
        actual["variance_components"]["within_group_variance"],
        expected["variance_components"]["within_group_variance"],
        rel_tol=1e-4
    )
    assert math.isclose(
        actual["variance_components"]["between_group_variance"],
        expected["variance_components"]["between_group_variance"],
        rel_tol=1e-4
    )


def test_model_summary():
    """Verify model summary contains correct metadata."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert actual["model_summary"]["n_groups"] == expected["model_summary"]["n_groups"]
    assert actual["model_summary"]["total_observations"] == expected["model_summary"]["total_observations"]
    assert math.isclose(
        actual["model_summary"]["effective_parameters"],
        expected["model_summary"]["effective_parameters"],
        rel_tol=1e-3
    )
    assert math.isclose(
        actual["model_summary"]["grand_mean"],
        expected["model_summary"]["grand_mean"],
        rel_tol=1e-4
    ), (
        f"grand_mean: got {actual['model_summary']['grand_mean']}, "
        f"expected {expected['model_summary']['grand_mean']}"
    )


def test_waic():
    """Verify WAIC model comparison criterion is computed correctly.

    WAIC provides an alternative to DIC using the log pointwise predictive
    density. The effective parameters via WAIC may differ from the DIC
    estimate depending on posterior variance structure.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert math.isclose(
        actual["model_comparison"]["waic"],
        expected["model_comparison"]["waic"],
        rel_tol=1e-3
    ), (
        f"WAIC: got {actual['model_comparison']['waic']}, "
        f"expected {expected['model_comparison']['waic']}"
    )
    assert math.isclose(
        actual["model_comparison"]["model_complexity_ratio"],
        expected["model_comparison"]["model_complexity_ratio"],
        rel_tol=1e-3
    ), (
        f"model_complexity_ratio: got {actual['model_comparison']['model_complexity_ratio']}, "
        f"expected {expected['model_comparison']['model_complexity_ratio']}"
    )


def test_intraclass_correlation():
    """Verify intraclass correlation coefficient (ICC) is correct.

    ICC = between_group_variance / total_variance measures the proportion
    of total variability attributable to group-level differences.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert math.isclose(
        actual["variance_components"]["intraclass_correlation"],
        expected["variance_components"]["intraclass_correlation"],
        rel_tol=1e-4
    ), (
        f"ICC: got {actual['variance_components']['intraclass_correlation']}, "
        f"expected {expected['variance_components']['intraclass_correlation']}"
    )
    assert math.isclose(
        actual["variance_components"]["total_variance"],
        expected["variance_components"]["total_variance"],
        rel_tol=1e-4
    ), (
        f"total_variance: got {actual['variance_components']['total_variance']}, "
        f"expected {expected['variance_components']['total_variance']}"
    )


def test_diagnostics():
    """Verify diagnostic summary statistics are computed correctly.

    Diagnostics aggregate shrinkage factors and interval widths across
    groups, providing a quick assessment of model behavior.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    assert math.isclose(
        actual["diagnostics"]["mean_shrinkage_factor"],
        expected["diagnostics"]["mean_shrinkage_factor"],
        rel_tol=1e-4
    ), (
        f"mean_shrinkage_factor: got {actual['diagnostics']['mean_shrinkage_factor']}, "
        f"expected {expected['diagnostics']['mean_shrinkage_factor']}"
    )
    assert math.isclose(
        actual["diagnostics"]["mean_interval_width"],
        expected["diagnostics"]["mean_interval_width"],
        rel_tol=1e-3
    ), (
        f"mean_interval_width: got {actual['diagnostics']['mean_interval_width']}, "
        f"expected {expected['diagnostics']['mean_interval_width']}"
    )
