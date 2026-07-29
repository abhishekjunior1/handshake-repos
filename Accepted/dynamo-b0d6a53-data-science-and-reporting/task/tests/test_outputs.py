"""Tests for the A/B test experiment analysis pipeline.

Validates that the pipeline correctly applies multiple testing correction
to all metrics, uses appropriate variance for power analysis, and produces
accurate hypothesis test results and effect size estimates.
"""

import json

EXPECTED_PATH = '/tests/expected_output.json'
OUTPUT_PATH = '/app/output.json'


def load_outputs():
    """Load expected and actual output files."""
    with open(EXPECTED_PATH, 'r') as f:
        expected = json.load(f)
    with open(OUTPUT_PATH, 'r') as f:
        actual = json.load(f)
    return expected, actual


def approx_equal(a, b, rel_tol=1e-3, abs_tol=1e-6):
    """Check if two values are approximately equal."""
    if a == b:
        return True
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if abs(a) < abs_tol and abs(b) < abs_tol:
            return True
        return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)
    return a == b


class TestPrimaryMetric:
    """Tests for primary metric hypothesis test results."""

    def test_primary_p_value(self):
        """Verify primary metric p-value is correctly computed."""
        expected, actual = load_outputs()
        assert approx_equal(actual['primary_metric']['p_value'], expected['primary_metric']['p_value']), \
            f"Primary p-value: expected {expected['primary_metric']['p_value']}, got {actual['primary_metric']['p_value']}"

    def test_primary_corrected_p(self):
        """Verify primary metric receives multiple testing correction."""
        expected, actual = load_outputs()
        assert approx_equal(actual['primary_metric']['corrected_p_value'], expected['primary_metric']['corrected_p_value']), \
            f"Primary corrected p: expected {expected['primary_metric']['corrected_p_value']}, got {actual['primary_metric']['corrected_p_value']}"


class TestSecondaryMetrics:
    """Tests for secondary metric correction application."""

    def test_secondary_count(self):
        """Verify correct number of secondary metrics analyzed."""
        expected, actual = load_outputs()
        assert len(actual['secondary_metrics']) == len(expected['secondary_metrics']), \
            f"Secondary count: expected {len(expected['secondary_metrics'])}, got {len(actual['secondary_metrics'])}"

    def test_secondary_corrected_p_values(self):
        """Verify secondary metrics receive proper multiple testing correction."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['secondary_metrics'], actual['secondary_metrics'])):
            assert approx_equal(act['corrected_p_value'], exp['corrected_p_value']), \
                f"Secondary {i} corrected_p: expected {exp['corrected_p_value']}, got {act['corrected_p_value']}"

    def test_secondary_significance(self):
        """Verify secondary significance uses corrected p-values."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['secondary_metrics'], actual['secondary_metrics'])):
            assert act['significant_corrected'] == exp['significant_corrected'], \
                f"Secondary {i} significance: expected {exp['significant_corrected']}, got {act['significant_corrected']}"


class TestPowerAnalysis:
    """Tests for statistical power estimation."""

    def test_observed_power(self):
        """Verify power is computed using appropriate variance estimate."""
        expected, actual = load_outputs()
        assert approx_equal(actual['power_analysis']['observed_power'], expected['power_analysis']['observed_power']), \
            f"Power: expected {expected['power_analysis']['observed_power']}, got {actual['power_analysis']['observed_power']}"

    def test_mde(self):
        """Verify minimum detectable effect uses correct variance."""
        expected, actual = load_outputs()
        assert approx_equal(actual['power_analysis']['minimum_detectable_effect'], expected['power_analysis']['minimum_detectable_effect']), \
            f"MDE: expected {expected['power_analysis']['minimum_detectable_effect']}, got {actual['power_analysis']['minimum_detectable_effect']}"


class TestEffectSize:
    """Tests for effect size computation."""

    def test_hedges_g(self):
        """Verify Hedges' g bias-corrected effect size."""
        expected, actual = load_outputs()
        assert approx_equal(actual['effect_size']['hedges_g'], expected['effect_size']['hedges_g']), \
            f"Hedges' g: expected {expected['effect_size']['hedges_g']}, got {actual['effect_size']['hedges_g']}"

    def test_confidence_interval(self):
        """Verify confidence interval for treatment effect."""
        expected, actual = load_outputs()
        assert approx_equal(actual['confidence_interval']['lower'], expected['confidence_interval']['lower']), \
            f"CI lower: expected {expected['confidence_interval']['lower']}, got {actual['confidence_interval']['lower']}"
        assert approx_equal(actual['confidence_interval']['upper'], expected['confidence_interval']['upper']), \
            f"CI upper: expected {expected['confidence_interval']['upper']}, got {actual['confidence_interval']['upper']}"


class TestCorrectionInfo:
    """Tests for correction metadata."""

    def test_n_tests(self):
        """Verify total test count includes all metrics."""
        expected, actual = load_outputs()
        assert actual['correction_info']['n_tests'] == expected['correction_info']['n_tests']

    def test_method(self):
        """Verify correction method is correctly reported."""
        expected, actual = load_outputs()
        assert actual['correction_info']['method'] == expected['correction_info']['method']
