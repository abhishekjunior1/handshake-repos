"""
Verification tests for model comparison benchmark pipeline.

Compares pipeline output against expected results on hidden evaluation data.
All numeric comparisons use relative tolerance of 1e-4.
"""

import json
import math
import os

import pytest


@pytest.fixture
def pipeline_output():
    """Load the pipeline's output file."""
    output_path = "/app/output.json"
    assert os.path.exists(output_path), f"Output file not found: {output_path}"
    with open(output_path) as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected output for comparison."""
    expected_path = "/tests/expected_output.json"
    assert os.path.exists(expected_path), f"Expected output not found: {expected_path}"
    with open(expected_path) as f:
        return json.load(f)


def approx_equal(actual, expected, rel_tol=1e-4):
    """Check if two numeric values are approximately equal."""
    if isinstance(expected, bool) or isinstance(actual, bool):
        return actual == expected
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        if expected == 0:
            return abs(actual) < 1e-8
        return abs(actual - expected) / max(abs(expected), 1e-15) < rel_tol
    return actual == expected


def test_benchmark_summary(pipeline_output, expected_output):
    """Verify benchmark summary contains correct metadata about the evaluation configuration."""
    actual = pipeline_output["benchmark_summary"]
    expected = expected_output["benchmark_summary"]
    assert actual["n_models"] == expected["n_models"]
    assert actual["n_datasets"] == expected["n_datasets"]
    assert actual["n_folds"] == expected["n_folds"]
    assert actual["n_metrics"] == expected["n_metrics"]
    assert actual["total_evaluations"] == expected["total_evaluations"]


def test_ranking_order(pipeline_output, expected_output):
    """Verify model rankings use mean rank ordering (not mean accuracy ordering)."""
    actual_rankings = pipeline_output["model_rankings"]["rankings"]
    expected_rankings = expected_output["model_rankings"]["rankings"]

    actual_order = [r["model"] for r in actual_rankings]
    expected_order = [r["model"] for r in expected_rankings]
    assert actual_order == expected_order, (
        f"Ranking order mismatch: got {actual_order}, expected {expected_order}. "
        f"Rankings should be ordered by mean rank across datasets."
    )


def test_ranking_values(pipeline_output, expected_output):
    """Verify mean rank values and positions are correctly computed."""
    actual_rankings = pipeline_output["model_rankings"]["rankings"]
    expected_rankings = expected_output["model_rankings"]["rankings"]

    for actual, expected in zip(actual_rankings, expected_rankings):
        assert actual["model"] == expected["model"]
        assert approx_equal(actual["mean_rank"], expected["mean_rank"]), (
            f"Mean rank for {actual['model']}: got {actual['mean_rank']}, "
            f"expected {expected['mean_rank']}"
        )
        assert approx_equal(actual["position"], expected["position"]), (
            f"Position for {actual['model']}: got {actual['position']}, "
            f"expected {expected['position']}"
        )
        assert approx_equal(actual["std_rank"], expected["std_rank"]), (
            f"Std rank for {actual['model']}: got {actual['std_rank']}, "
            f"expected {expected['std_rank']}"
        )
        assert approx_equal(actual["best_rank"], expected["best_rank"]), (
            f"Best rank for {actual['model']}: got {actual['best_rank']}, "
            f"expected {expected['best_rank']}"
        )
        assert approx_equal(actual["worst_rank"], expected["worst_rank"]), (
            f"Worst rank for {actual['model']}: got {actual['worst_rank']}, "
            f"expected {expected['worst_rank']}"
        )


def test_significance_count(pipeline_output, expected_output):
    """Verify the number of statistically significant comparisons matches expected."""
    actual = pipeline_output["statistical_significance"]
    expected = expected_output["statistical_significance"]
    assert actual["n_significant"] == expected["n_significant"], (
        f"Significant comparisons: got {actual['n_significant']}, "
        f"expected {expected['n_significant']}. "
        f"Significance testing should use fold-level paired observations."
    )
    assert actual["n_total"] == expected["n_total"]


def test_significance_values(pipeline_output, expected_output):
    """Verify pairwise t-statistics and p-values from fold-level paired testing."""
    actual_comps = pipeline_output["statistical_significance"]["pairwise_comparisons"]
    expected_comps = expected_output["statistical_significance"]["pairwise_comparisons"]

    assert len(actual_comps) == len(expected_comps)

    for actual, expected in zip(actual_comps, expected_comps):
        assert actual["model_a"] == expected["model_a"]
        assert actual["model_b"] == expected["model_b"]
        assert approx_equal(actual["t_statistic"], expected["t_statistic"]), (
            f"t-statistic for {actual['model_a']} vs {actual['model_b']}: "
            f"got {actual['t_statistic']}, expected {expected['t_statistic']}"
        )
        assert approx_equal(actual["p_value"], expected["p_value"]), (
            f"p-value for {actual['model_a']} vs {actual['model_b']}: "
            f"got {actual['p_value']}, expected {expected['p_value']}"
        )
        assert actual["significant"] == expected["significant"], (
            f"Significance for {actual['model_a']} vs {actual['model_b']}: "
            f"got {actual['significant']}, expected {expected['significant']}"
        )
        assert approx_equal(actual["corrected_p_value"], expected["corrected_p_value"]), (
            f"Corrected p-value for {actual['model_a']} vs {actual['model_b']}: "
            f"got {actual['corrected_p_value']}, expected {expected['corrected_p_value']}"
        )
        assert approx_equal(actual["mean_difference"], expected["mean_difference"]), (
            f"Mean difference for {actual['model_a']} vs {actual['model_b']}: "
            f"got {actual['mean_difference']}, expected {expected['mean_difference']}"
        )


def test_normalized_scores(pipeline_output, expected_output):
    """Verify per-dataset min-max normalized scores are correctly computed."""
    actual = pipeline_output["score_normalization"]["normalized_scores"]
    expected = expected_output["score_normalization"]["normalized_scores"]

    assert set(actual.keys()) == set(expected.keys()), (
        f"Dataset keys mismatch: got {set(actual.keys())}, expected {set(expected.keys())}"
    )

    for dataset in expected:
        assert dataset in actual
        for model in expected[dataset]:
            assert model in actual[dataset], (
                f"Missing model {model} in normalized scores for {dataset}"
            )
            assert approx_equal(actual[dataset][model], expected[dataset][model]), (
                f"Normalized score for {model} on {dataset}: "
                f"got {actual[dataset][model]}, expected {expected[dataset][model]}. "
                f"Normalization should use per-dataset min-max scaling."
            )


def test_aggregate_scores(pipeline_output, expected_output):
    """Verify aggregate performance scores computed from normalized per-dataset scores."""
    actual = pipeline_output["aggregate_performance"]["aggregate_scores"]
    expected = expected_output["aggregate_performance"]["aggregate_scores"]

    assert actual.get("aggregation_method", pipeline_output["aggregate_performance"].get("aggregation_method")) is not None

    for model in expected:
        assert model in actual, f"Missing model {model} in aggregate scores"
        assert approx_equal(actual[model], expected[model]), (
            f"Aggregate score for {model}: got {actual[model]}, expected {expected[model]}"
        )


def test_aggregate_method(pipeline_output, expected_output):
    """Verify the correct aggregation method is reported in the output."""
    actual_method = pipeline_output["aggregate_performance"]["aggregation_method"]
    expected_method = expected_output["aggregate_performance"]["aggregation_method"]
    assert actual_method == expected_method, (
        f"Aggregation method: got {actual_method}, expected {expected_method}"
    )
