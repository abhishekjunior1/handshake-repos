"""
Verification tests for the extreme value analysis pipeline.
Tests pipeline output against expected values from the correctly-fixed
pipeline on hidden data with temporal clustering.
"""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_outputs():
    """Load actual and expected outputs."""
    with open(OUTPUT_PATH, "r") as f:
        actual = json.load(f)
    with open(EXPECTED_PATH, "r") as f:
        expected = json.load(f)
    return actual, expected


def approx_equal(a, b, rel_tol=0.05):
    """Check approximate equality with relative tolerance."""
    if b == 0:
        return abs(a) < 1e-6
    return abs(a - b) / abs(b) <= rel_tol


class TestGEVParameters:
    """Tests for GEV distribution parameters from block maxima."""

    def test_gev_location(self):
        """Verify GEV location parameter within 5% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["gev_params"]["location"], expected["gev_params"]["location"])

    def test_gev_scale(self):
        """Verify GEV scale parameter within 5% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["gev_params"]["scale"], expected["gev_params"]["scale"])

    def test_gev_shape(self):
        """Verify GEV shape parameter within 10% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["gev_params"]["shape"], expected["gev_params"]["shape"], rel_tol=0.10)


class TestGPDParameters:
    """Tests for GPD parameters from declustered peaks."""

    def test_gpd_scale(self):
        """Verify GPD scale parameter within 10% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["gpd_params"]["scale"], expected["gpd_params"]["scale"], rel_tol=0.10), \
            f"GPD scale: {actual['gpd_params']['scale']} vs {expected['gpd_params']['scale']}"

    def test_gpd_shape(self):
        """Verify GPD shape parameter within 10% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["gpd_params"]["shape"], expected["gpd_params"]["shape"], rel_tol=0.10), \
            f"GPD shape: {actual['gpd_params']['shape']} vs {expected['gpd_params']['shape']}"


class TestReturnLevels:
    """Tests for computed return levels at multiple periods."""

    def test_return_level_10yr(self):
        """Verify 10-year return level within 10% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["return_levels"]["10"], expected["return_levels"]["10"], rel_tol=0.10), \
            f"10yr RL: {actual['return_levels']['10']} vs {expected['return_levels']['10']}"

    def test_return_level_25yr(self):
        """Verify 25-year return level within 5% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["return_levels"]["25"], expected["return_levels"]["25"], rel_tol=0.05), \
            f"25yr RL: {actual['return_levels']['25']} vs {expected['return_levels']['25']}"

    def test_return_level_100yr(self):
        """Verify 100-year return level within 5% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["return_levels"]["100"], expected["return_levels"]["100"], rel_tol=0.05), \
            f"100yr RL: {actual['return_levels']['100']} vs {expected['return_levels']['100']}"


class TestClusterStatistics:
    """Tests for declustering and cluster statistics."""

    def test_exceedance_count(self):
        """Verify total exceedance count matches expected."""
        actual, expected = load_outputs()
        assert actual["exceedance_count"] == expected["exceedance_count"]

    def test_cluster_count(self):
        """Verify cluster count matches expected."""
        actual, expected = load_outputs()
        assert actual["cluster_count"] == expected["cluster_count"]

    def test_extremal_index(self):
        """Verify extremal index within 5% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["extremal_index"], expected["extremal_index"])

    def test_cluster_rate(self):
        """Verify cluster rate within 5% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["cluster_rate"], expected["cluster_rate"])


class TestDiagnostics:
    """Tests for diagnostic statistics."""

    def test_qq_correlation(self):
        """Verify QQ-plot correlation within 3% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["qq_statistics"]["correlation"], expected["qq_statistics"]["correlation"], rel_tol=0.03)

    def test_goodness_of_fit(self):
        """Verify goodness-of-fit pass/fail matches expected."""
        actual, expected = load_outputs()
        assert actual["goodness_of_fit"]["pass"] == expected["goodness_of_fit"]["pass"]


class TestBlockMaxima:
    """Tests for block maxima summary."""

    def test_block_count(self):
        """Verify block count matches expected."""
        actual, expected = load_outputs()
        assert actual["block_maxima_summary"]["count"] == expected["block_maxima_summary"]["count"]

    def test_block_max(self):
        """Verify block maxima maximum within 3% of expected."""
        actual, expected = load_outputs()
        assert approx_equal(actual["block_maxima_summary"]["max"], expected["block_maxima_summary"]["max"], rel_tol=0.03)


class TestDiagnosticFlags:
    """Tests for diagnostic flag values."""

    def test_shape_significant(self):
        """Verify shape significance flag matches expected."""
        actual, expected = load_outputs()
        assert actual["diagnostic_flags"]["shape_significant"] == expected["diagnostic_flags"]["shape_significant"]

    def test_fit_adequate(self):
        """Verify fit adequacy flag matches expected."""
        actual, expected = load_outputs()
        assert actual["diagnostic_flags"]["fit_adequate"] == expected["diagnostic_flags"]["fit_adequate"]
