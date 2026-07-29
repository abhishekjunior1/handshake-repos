"""Tests for A/B experiment analysis pipeline output correctness.

Validates the pipeline produces correct results on multi-metric experiment
data with unequal variances and small sample sizes.
"""

import json
import math
import os

import pytest


@pytest.fixture
def pipeline_output():
    """Load the pipeline output from /app/output.json."""
    output_path = "/app/output.json"
    with open(output_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected correct output."""
    expected_path = os.path.join(os.path.dirname(__file__), "expected_output.json")
    with open(expected_path, 'r') as f:
        return json.load(f)


def test_power_analysis_achieved_power(pipeline_output, expected_output):
    """Verify that achieved statistical power is computed using the correct
    significance level for the primary metric test."""
    actual = pipeline_output["power_analysis"]["achieved_power"]
    expected = expected_output["power_analysis"]["achieved_power"]
    
    assert math.isclose(actual, expected, rel_tol=1e-4), \
        f"Achieved power mismatch: got {actual}, expected {expected}"


def test_power_mde_absolute(pipeline_output, expected_output):
    """Verify the minimum detectable effect uses the correct alpha level."""
    actual = pipeline_output["power_analysis"]["mde"]["absolute"]
    expected = expected_output["power_analysis"]["mde"]["absolute"]
    
    assert math.isclose(actual, expected, rel_tol=1e-4), \
        f"MDE absolute mismatch: got {actual}, expected {expected}"


def test_power_mde_relative(pipeline_output, expected_output):
    """Verify relative MDE is consistent with the correct alpha computation."""
    actual = pipeline_output["power_analysis"]["mde"]["relative"]
    expected = expected_output["power_analysis"]["mde"]["relative"]
    
    assert math.isclose(actual, expected, rel_tol=1e-4), \
        f"MDE relative mismatch: got {actual}, expected {expected}"


def test_power_sample_size_recommendation(pipeline_output, expected_output):
    """Verify sample size recommendation uses the correct significance threshold."""
    actual_n = pipeline_output["power_analysis"]["sample_size_recommendation"]["n_per_group"]
    expected_n = expected_output["power_analysis"]["sample_size_recommendation"]["n_per_group"]
    
    assert actual_n == expected_n, \
        f"Sample size recommendation: got {actual_n}, expected {expected_n}"


def test_confidence_interval_primary_se(pipeline_output, expected_output):
    """Verify the primary metric CI standard error uses the correct variance
    estimates from each respective group."""
    actual_se = pipeline_output["metrics"][0]["confidence_interval"]["se_difference"]
    expected_se = expected_output["metrics"][0]["confidence_interval"]["se_difference"]
    
    assert math.isclose(actual_se, expected_se, rel_tol=1e-3), \
        f"Primary CI SE mismatch: got {actual_se}, expected {expected_se}"


def test_confidence_interval_primary_bounds(pipeline_output, expected_output):
    """Verify primary metric confidence interval bounds are computed correctly."""
    actual_ci = pipeline_output["metrics"][0]["confidence_interval"]
    expected_ci = expected_output["metrics"][0]["confidence_interval"]
    
    assert math.isclose(actual_ci["ci_lower"], expected_ci["ci_lower"], rel_tol=1e-3), \
        f"CI lower mismatch: got {actual_ci['ci_lower']}, expected {expected_ci['ci_lower']}"
    assert math.isclose(actual_ci["ci_upper"], expected_ci["ci_upper"], rel_tol=1e-3), \
        f"CI upper mismatch: got {actual_ci['ci_upper']}, expected {expected_ci['ci_upper']}"


def test_confidence_interval_secondary_metrics(pipeline_output, expected_output):
    """Verify secondary metric CIs use correct per-group variances."""
    for i in range(1, len(expected_output["metrics"])):
        actual_se = pipeline_output["metrics"][i]["confidence_interval"]["se_difference"]
        expected_se = expected_output["metrics"][i]["confidence_interval"]["se_difference"]
        
        assert math.isclose(actual_se, expected_se, rel_tol=1e-3), \
            f"Metric {i} CI SE mismatch: got {actual_se}, expected {expected_se}"


def test_confidence_interval_margin_of_error(pipeline_output, expected_output):
    """Verify margin of error reflects correct variance structure."""
    actual_margin = pipeline_output["metrics"][0]["confidence_interval"]["margin_of_error"]
    expected_margin = expected_output["metrics"][0]["confidence_interval"]["margin_of_error"]
    
    assert math.isclose(actual_margin, expected_margin, rel_tol=1e-3), \
        f"Margin of error mismatch: got {actual_margin}, expected {expected_margin}"


def test_multiple_testing_corrections_applied(pipeline_output, expected_output):
    """Verify all metrics have corrected p-values."""
    actual_adj = pipeline_output["multiple_testing"]["adjusted_p_values"]
    expected_adj = expected_output["multiple_testing"]["adjusted_p_values"]
    
    assert len(actual_adj) == len(expected_adj), \
        f"Adjusted p-value count: got {len(actual_adj)}, expected {len(expected_adj)}"
    
    for i, (a, e) in enumerate(zip(actual_adj, expected_adj)):
        assert math.isclose(a, e, rel_tol=1e-4), \
            f"Adjusted p-value {i}: got {a}, expected {e}"


def test_effect_sizes_computed(pipeline_output, expected_output):
    """Verify effect sizes include the finite-sample correction factor."""
    for i in range(len(expected_output["metrics"])):
        actual_g = pipeline_output["metrics"][i]["effect_size"]["hedges_g"]
        expected_g = expected_output["metrics"][i]["effect_size"]["hedges_g"]
        
        assert math.isclose(actual_g, expected_g, rel_tol=1e-4), \
            f"Metric {i} Hedges' g: got {actual_g}, expected {expected_g}"


def test_summary_power_consistent(pipeline_output, expected_output):
    """Verify summary correctly reflects achieved power from the analysis."""
    actual_power = pipeline_output["summary"]["achieved_power"]
    expected_power = expected_output["summary"]["achieved_power"]
    
    assert math.isclose(actual_power, expected_power, rel_tol=1e-4), \
        f"Summary power: got {actual_power}, expected {expected_power}"


def test_experiment_metadata_preserved(pipeline_output, expected_output):
    """Verify experiment metadata is correctly propagated to the report."""
    assert pipeline_output["experiment"]["id"] == expected_output["experiment"]["id"]
    assert pipeline_output["experiment"]["name"] == expected_output["experiment"]["name"]


def test_metrics_count(pipeline_output, expected_output):
    """Verify all metrics are analyzed and present in the report."""
    assert len(pipeline_output["metrics"]) == len(expected_output["metrics"]), \
        f"Metric count: got {len(pipeline_output['metrics'])}, expected {len(expected_output['metrics'])}"
