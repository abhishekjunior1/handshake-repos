"""Test suite for geostatistical pipeline output validation."""
import json
import pytest

EXPECTED_PATH = '/tests/expected_output.json'
OUTPUT_PATH = '/app/output.json'


@pytest.fixture
def expected():
    """Load expected output."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


@pytest.fixture
def actual():
    """Load actual pipeline output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


class TestVariogramModel:
    """Tests for fitted variogram model parameters."""

    def test_model_type(self, expected, actual):
        """Verify the correct variogram model type was used."""
        assert actual['variogram_model']['model_type'] == expected['variogram_model']['model_type']

    def test_nugget(self, expected, actual):
        """Verify nugget parameter is within tolerance."""
        assert abs(actual['variogram_model']['nugget'] - expected['variogram_model']['nugget']) < 0.1

    def test_sill(self, expected, actual):
        """Verify sill parameter matches expected value."""
        exp = expected['variogram_model']['sill']
        act = actual['variogram_model']['sill']
        tol = max(0.1, 0.15 * abs(exp))
        assert abs(act - exp) < tol, f"sill: got {act}, expected {exp}, tol {tol}"

    def test_range(self, expected, actual):
        """Verify range parameter matches expected value."""
        exp = expected['variogram_model']['range']
        act = actual['variogram_model']['range']
        tol = max(0.2, 0.15 * abs(exp))
        assert abs(act - exp) < tol, f"range: got {act}, expected {exp}, tol {tol}"


class TestCrossValidation:
    """Tests for cross-validation results."""

    def test_predictions(self, expected, actual):
        """Verify kriging predictions at cross-validation points."""
        exp_p = expected['cross_validation']['predictions']
        act_p = actual['cross_validation']['predictions']
        assert len(act_p) == len(exp_p), "Prediction count mismatch"
        for i, (e, a) in enumerate(zip(exp_p, act_p)):
            tol = max(0.15, 0.05 * abs(e))
            assert abs(a - e) < tol, f"prediction[{i}]: got {a}, expected {e}"

    def test_rmse(self, expected, actual):
        """Verify cross-validation RMSE within tolerance."""
        exp = expected['cross_validation']['rmse']
        act = actual['cross_validation']['rmse']
        tol = max(0.05, 0.1 * exp)
        assert abs(act - exp) < tol, f"rmse: got {act}, expected {exp}"

    def test_mean_error(self, expected, actual):
        """Verify cross-validation mean error."""
        exp = expected['cross_validation']['mean_error']
        act = actual['cross_validation']['mean_error']
        assert abs(act - exp) < 0.1, f"mean_error: got {act}, expected {exp}"

    def test_standardized_rmse(self, expected, actual):
        """Verify standardized RMSE reflects correct degrees-of-freedom scaling."""
        exp = expected['cross_validation']['standardized_rmse']
        act = actual['cross_validation']['standardized_rmse']
        tol = max(0.1, 0.1 * exp)
        assert abs(act - exp) < tol, f"standardized_rmse: got {act}, expected {exp}"

    def test_variances_positive(self, expected, actual):
        """Verify all kriging variances are non-negative."""
        for i, v in enumerate(actual['cross_validation']['variances']):
            assert v >= 0, f"variance[{i}] is negative: {v}"


class TestMetadata:
    """Tests for pipeline metadata."""

    def test_n_points(self, expected, actual):
        """Verify correct number of spatial points processed."""
        assert actual['metadata']['n_points'] == expected['metadata']['n_points']

    def test_n_lags(self, expected, actual):
        """Verify correct number of variogram lag bins."""
        assert actual['metadata']['n_lags'] == expected['metadata']['n_lags']
