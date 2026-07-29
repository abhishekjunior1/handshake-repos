"""Tests for meta-analysis pipeline output validation.

Compares the generated output.json against expected_output.json to verify
correctness of heterogeneity estimates, pooled effects, publication bias
tests, and prediction intervals.
"""

import json
import math
import os

import pytest


def load_json(filepath: str) -> dict:
    """Load a JSON file and return its contents as a dictionary."""
    with open(filepath, "r") as f:
        return json.load(f)


@pytest.fixture
def actual_output() -> dict:
    """Load the actual pipeline output."""
    return load_json("/app/output.json")


@pytest.fixture
def expected_output() -> dict:
    """Load the expected correct output."""
    return load_json("/tests/expected_output.json")


def approx_equal(a: float, b: float, tol: float = 0.001) -> bool:
    """Check if two floats are approximately equal within tolerance."""
    if abs(b) < 1e-10:
        return abs(a - b) < tol
    return abs(a - b) / max(abs(a), abs(b)) < tol


class TestHeterogeneity:
    """Tests for heterogeneity estimation correctness."""

    def test_tau_squared(self, actual_output, expected_output):
        """Verify that the DerSimonian-Laird tau-squared estimate matches expected value."""
        actual = actual_output["overall_analysis"]["heterogeneity"]["tau_squared"]
        expected = expected_output["overall_analysis"]["heterogeneity"]["tau_squared"]
        assert approx_equal(actual, expected), (
            f"tau_squared mismatch: got {actual}, expected {expected}"
        )

    def test_q_statistic(self, actual_output, expected_output):
        """Verify that Cochran's Q statistic is computed correctly."""
        actual = actual_output["overall_analysis"]["heterogeneity"]["Q"]
        expected = expected_output["overall_analysis"]["heterogeneity"]["Q"]
        assert approx_equal(actual, expected), (
            f"Q statistic mismatch: got {actual}, expected {expected}"
        )

    def test_i_squared(self, actual_output, expected_output):
        """Verify that the I-squared heterogeneity measure is correct."""
        actual = actual_output["overall_analysis"]["heterogeneity"]["I_squared"]
        expected = expected_output["overall_analysis"]["heterogeneity"]["I_squared"]
        assert approx_equal(actual, expected), (
            f"I_squared mismatch: got {actual}, expected {expected}"
        )


class TestPublicationBias:
    """Tests for Egger's regression test correctness."""

    def test_egger_intercept(self, actual_output, expected_output):
        """Verify that Egger's test intercept is computed with correct WLS weights."""
        actual = actual_output["publication_bias"]["intercept"]
        expected = expected_output["publication_bias"]["intercept"]
        assert approx_equal(actual, expected), (
            f"Egger intercept mismatch: got {actual}, expected {expected}"
        )

    def test_egger_slope(self, actual_output, expected_output):
        """Verify that Egger's test slope uses proper inverse-variance weights."""
        actual = actual_output["publication_bias"]["slope"]
        expected = expected_output["publication_bias"]["slope"]
        assert approx_equal(actual, expected), (
            f"Egger slope mismatch: got {actual}, expected {expected}"
        )

    def test_egger_p_value(self, actual_output, expected_output):
        """Verify that the p-value for publication bias is correctly computed."""
        actual = actual_output["publication_bias"]["p_intercept"]
        expected = expected_output["publication_bias"]["p_intercept"]
        assert approx_equal(actual, expected, tol=0.01), (
            f"Egger p_intercept mismatch: got {actual}, expected {expected}"
        )


class TestPredictionInterval:
    """Tests for prediction interval computation."""

    def test_prediction_interval_lower(self, actual_output, expected_output):
        """Verify lower bound of prediction interval uses correct t-distribution df."""
        actual = actual_output["overall_analysis"]["random_effects"]["prediction_interval_lower"]
        expected = expected_output["overall_analysis"]["random_effects"]["prediction_interval_lower"]
        assert approx_equal(actual, expected), (
            f"PI lower mismatch: got {actual}, expected {expected}"
        )

    def test_prediction_interval_upper(self, actual_output, expected_output):
        """Verify upper bound of prediction interval uses correct t-distribution df."""
        actual = actual_output["overall_analysis"]["random_effects"]["prediction_interval_upper"]
        expected = expected_output["overall_analysis"]["random_effects"]["prediction_interval_upper"]
        assert approx_equal(actual, expected), (
            f"PI upper mismatch: got {actual}, expected {expected}"
        )


class TestPooledEstimates:
    """Tests for pooled effect estimates."""

    def test_random_effects_pooled(self, actual_output, expected_output):
        """Verify the random-effects pooled estimate is correctly computed."""
        actual = actual_output["overall_analysis"]["random_effects"]["pooled_estimate"]
        expected = expected_output["overall_analysis"]["random_effects"]["pooled_estimate"]
        assert approx_equal(actual, expected), (
            f"RE pooled mismatch: got {actual}, expected {expected}"
        )

    def test_fixed_effect_pooled(self, actual_output, expected_output):
        """Verify the fixed-effect pooled estimate is correctly computed."""
        actual = actual_output["overall_analysis"]["fixed_effect"]["pooled_estimate"]
        expected = expected_output["overall_analysis"]["fixed_effect"]["pooled_estimate"]
        assert approx_equal(actual, expected), (
            f"FE pooled mismatch: got {actual}, expected {expected}"
        )

    def test_confidence_interval(self, actual_output, expected_output):
        """Verify the confidence interval bounds for the random-effects model."""
        actual_lower = actual_output["overall_analysis"]["random_effects"]["ci_lower"]
        expected_lower = expected_output["overall_analysis"]["random_effects"]["ci_lower"]
        actual_upper = actual_output["overall_analysis"]["random_effects"]["ci_upper"]
        expected_upper = expected_output["overall_analysis"]["random_effects"]["ci_upper"]
        assert approx_equal(actual_lower, expected_lower), (
            f"CI lower mismatch: got {actual_lower}, expected {expected_lower}"
        )
        assert approx_equal(actual_upper, expected_upper), (
            f"CI upper mismatch: got {actual_upper}, expected {expected_upper}"
        )


class TestSubgroupAnalyses:
    """Tests for subgroup-specific analyses."""

    def test_subgroup_count(self, actual_output, expected_output):
        """Verify correct number of subgroups are analyzed."""
        actual = len(actual_output["subgroup_analyses"])
        expected = len(expected_output["subgroup_analyses"])
        assert actual == expected, (
            f"Subgroup count mismatch: got {actual}, expected {expected}"
        )

    def test_subgroup_pooled_estimates(self, actual_output, expected_output):
        """Verify pooled estimates for each subgroup with sufficient studies."""
        for actual_sg, expected_sg in zip(
            actual_output["subgroup_analyses"],
            expected_output["subgroup_analyses"],
        ):
            if expected_sg["analysis"] is None:
                assert actual_sg["analysis"] is None
                continue
            actual_pooled = actual_sg["analysis"]["random_effects"]["pooled_estimate"]
            expected_pooled = expected_sg["analysis"]["random_effects"]["pooled_estimate"]
            assert approx_equal(actual_pooled, expected_pooled), (
                f"Subgroup '{expected_sg['subgroup']}' pooled mismatch: "
                f"got {actual_pooled}, expected {expected_pooled}"
            )


class TestBetweenSubgroupHeterogeneity:
    """Tests for between-subgroup heterogeneity statistics."""

    def test_q_between(self, actual_output, expected_output):
        """Verify between-subgroup Q statistic is correctly computed."""
        actual = actual_output["between_subgroup_heterogeneity"]["Q_between"]
        expected = expected_output["between_subgroup_heterogeneity"]["Q_between"]
        assert approx_equal(actual, expected), (
            f"Q_between mismatch: got {actual}, expected {expected}"
        )

    def test_between_df(self, actual_output, expected_output):
        """Verify degrees of freedom for between-subgroup test."""
        actual = actual_output["between_subgroup_heterogeneity"]["df"]
        expected = expected_output["between_subgroup_heterogeneity"]["df"]
        assert actual == expected, (
            f"Between-subgroup df mismatch: got {actual}, expected {expected}"
        )

    def test_between_p_value(self, actual_output, expected_output):
        """Verify p-value for between-subgroup heterogeneity test."""
        actual = actual_output["between_subgroup_heterogeneity"]["p_value"]
        expected = expected_output["between_subgroup_heterogeneity"]["p_value"]
        assert approx_equal(actual, expected, tol=0.01), (
            f"Between-subgroup p_value mismatch: got {actual}, expected {expected}"
        )
