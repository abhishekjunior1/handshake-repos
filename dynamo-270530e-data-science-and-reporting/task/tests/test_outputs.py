"""
Verification tests for Singular Spectrum Analysis (SSA) pipeline.
Compares pipeline output against expected results from correct implementation.
"""

import json
import math
import os

import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = '/app/output.json'
EXPECTED_PATH = os.path.join(TESTS_DIR, 'expected_output.json')


@pytest.fixture
def output():
    """Load the pipeline output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Load the expected output."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-9, abs_tol=1e-12):
    """Check if two floats are approximately equal."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)


def assert_vectors_equal(actual, expected_vec, name, rel_tol=1e-9):
    """Assert two vectors are element-wise approximately equal."""
    assert len(actual) == len(expected_vec), \
        f"{name}: length mismatch ({len(actual)} vs {len(expected_vec)})"
    for i, (a, e) in enumerate(zip(actual, expected_vec)):
        assert approx_equal(a, e, rel_tol=rel_tol), \
            f"{name}[{i}]: {a} != {e} (rel_tol={rel_tol})"


class TestReconstructedComponents:
    """Tests for the reconstructed time series components."""

    def test_components_count(self, output, expected):
        """Verify that the number of reconstructed component groups matches expected."""
        assert len(output['reconstructed_components']) == len(expected['reconstructed_components']), \
            "Reconstructed components group count mismatch"

    def test_components_values(self, output, expected):
        """Verify that reconstructed component values match expected within tolerance."""
        for k in range(len(expected['reconstructed_components'])):
            assert_vectors_equal(
                output['reconstructed_components'][k],
                expected['reconstructed_components'][k],
                f"reconstructed_components[{k}]"
            )


class TestContributionRatios:
    """Tests for the variance contribution ratios per group."""

    def test_contribution_ratios_count(self, output, expected):
        """Verify the number of contribution ratio values matches expected."""
        assert len(output['contribution_ratios']) == len(expected['contribution_ratios']), \
            "Contribution ratios count mismatch"

    def test_contribution_ratios_values(self, output, expected):
        """Verify contribution ratio values match expected within tolerance."""
        for k in range(len(expected['contribution_ratios'])):
            assert approx_equal(
                output['contribution_ratios'][k],
                expected['contribution_ratios'][k],
                rel_tol=1e-8
            ), f"contribution_ratios[{k}]: {output['contribution_ratios'][k]} != " \
               f"{expected['contribution_ratios'][k]}"


class TestEigenvalueSpectrum:
    """Tests for the singular value spectrum from SVD."""

    def test_eigenvalue_count(self, output, expected):
        """Verify the number of reported singular values matches expected."""
        assert len(output['eigenvalue_spectrum']) == len(expected['eigenvalue_spectrum']), \
            "Eigenvalue spectrum count mismatch"

    def test_eigenvalue_values(self, output, expected):
        """Verify singular values match expected within tolerance."""
        for k in range(len(expected['eigenvalue_spectrum'])):
            assert approx_equal(
                output['eigenvalue_spectrum'][k],
                expected['eigenvalue_spectrum'][k],
                rel_tol=1e-8
            ), f"eigenvalue_spectrum[{k}]: {output['eigenvalue_spectrum'][k]} != " \
               f"{expected['eigenvalue_spectrum'][k]}"


class TestWCorrelationMatrix:
    """Tests for the weighted correlation (w-correlation) matrix."""

    def test_wcorr_dimensions(self, output, expected):
        """Verify the w-correlation matrix has correct dimensions."""
        assert len(output['w_correlation_matrix']) == len(expected['w_correlation_matrix']), \
            "W-correlation matrix row count mismatch"

    def test_wcorr_values(self, output, expected):
        """Verify w-correlation matrix values match expected within tolerance."""
        for i in range(len(expected['w_correlation_matrix'])):
            assert_vectors_equal(
                output['w_correlation_matrix'][i],
                expected['w_correlation_matrix'][i],
                f"w_correlation_matrix[{i}]",
                rel_tol=1e-8
            )


class TestResidualSeries:
    """Tests for the reconstruction residual series."""

    def test_residual_length(self, output, expected):
        """Verify residual series has correct length."""
        assert len(output['residual_series']) == len(expected['residual_series']), \
            "Residual series length mismatch"

    def test_residual_values(self, output, expected):
        """Verify residual series values match expected within tolerance."""
        assert_vectors_equal(
            output['residual_series'],
            expected['residual_series'],
            "residual_series",
            rel_tol=1e-8
        )


class TestDiagnostics:
    """Tests for the diagnostic output fields."""

    def test_trajectory_norm(self, output, expected):
        """Verify the trajectory matrix Frobenius norm matches expected."""
        assert approx_equal(
            output['diagnostics']['trajectory_norm'],
            expected['diagnostics']['trajectory_norm'],
            rel_tol=1e-8
        ), f"trajectory_norm mismatch"

    def test_effective_rank(self, output, expected):
        """Verify the effective rank estimate matches expected."""
        assert output['diagnostics']['effective_rank'] == \
            expected['diagnostics']['effective_rank'], \
            "effective_rank mismatch"

    def test_trend_correlation(self, output, expected):
        """Verify trend correlation values match expected."""
        out_tc = output['diagnostics']['trend_correlation']
        exp_tc = expected['diagnostics']['trend_correlation']
        # Normalize both to lists for uniform comparison
        if not isinstance(out_tc, list):
            out_tc = [out_tc]
        if not isinstance(exp_tc, list):
            exp_tc = [exp_tc]
        assert len(out_tc) == len(exp_tc), \
            f"trend_correlation length mismatch: {len(out_tc)} vs {len(exp_tc)}"
        for k in range(len(exp_tc)):
            assert approx_equal(out_tc[k], exp_tc[k], rel_tol=1e-2), \
                f"trend_correlation[{k}]: {out_tc[k]} != {exp_tc[k]}"

    def test_total_variance_explained(self, output, expected):
        """Verify total variance explained matches expected."""
        assert approx_equal(
            output['diagnostics']['total_variance_explained'],
            expected['diagnostics']['total_variance_explained'],
            rel_tol=1e-8
        ), "total_variance_explained mismatch"
