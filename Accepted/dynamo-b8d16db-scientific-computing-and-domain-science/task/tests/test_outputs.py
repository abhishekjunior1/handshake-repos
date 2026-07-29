"""
Tests for the adaptive quadrature integration pipeline output.
Verifies the pipeline produces correct results on hidden test data.
"""

import json
import os
import math
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


@pytest.fixture
def output():
    """Load the pipeline output."""
    with open(OUTPUT_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Load the expected output."""
    with open(EXPECTED_PATH, 'r') as f:
        return json.load(f)


def test_integral_value(output, expected):
    """Verify the computed integral value matches expected within tolerance."""
    assert math.isclose(
        output["integral_value"], expected["integral_value"],
        rel_tol=1e-7, abs_tol=1e-11
    ), (
        f"integral_value mismatch: got {output['integral_value']}, "
        f"expected {expected['integral_value']}"
    )


def test_error_estimate(output, expected):
    """Verify the error estimate is within acceptable bounds."""
    if expected["error_estimate"] > 0:
        ratio = output["error_estimate"] / expected["error_estimate"]
        assert 0.2 <= ratio <= 5.0, (
            f"error_estimate ratio out of range: got {output['error_estimate']}, "
            f"expected {expected['error_estimate']}, ratio={ratio:.2f}"
        )
    else:
        assert output["error_estimate"] >= 0


def test_subdivisions(output, expected):
    """Verify the number of adaptive subdivisions is consistent with correct behavior."""
    expected_subs = expected["subdivisions"]
    actual_subs = output["subdivisions"]
    if expected_subs > 0:
        assert abs(actual_subs - expected_subs) <= max(3, expected_subs * 0.15), (
            f"subdivisions mismatch: got {actual_subs}, expected {expected_subs}"
        )
    else:
        assert actual_subs == 0, (
            f"Expected 0 subdivisions but got {actual_subs}"
        )


def test_convergence_order(output, expected):
    """Verify the convergence order is estimated correctly."""
    expected_order = expected["convergence_order"]
    actual_order = output["convergence_order"]
    if expected_order > 0:
        assert math.isclose(actual_order, expected_order, rel_tol=0.08), (
            f"convergence_order mismatch: got {actual_order}, expected {expected_order}"
        )
    else:
        assert actual_order >= 0


def test_singularity_strength(output, expected):
    """Verify the singularity strength detection."""
    expected_strength = expected["singularity_strength"]
    actual_strength = output["singularity_strength"]
    assert math.isclose(actual_strength, expected_strength, abs_tol=0.05), (
        f"singularity_strength mismatch: got {actual_strength}, expected {expected_strength}"
    )


def test_method_info_present(output, expected):
    """Verify method_info contains required diagnostic fields."""
    assert "method_info" in output, "Missing method_info field"
    assert "method" in output["method_info"], "Missing method field in method_info"


def test_output_schema(output):
    """Verify all required output fields are present with correct types."""
    required_fields = {
        "integral_value": (int, float),
        "error_estimate": (int, float),
        "subdivisions": int,
        "convergence_order": (int, float),
        "singularity_strength": (int, float),
        "method_info": dict
    }
    for field, expected_type in required_fields.items():
        assert field in output, f"Missing required field: {field}"
        assert isinstance(output[field], expected_type), (
            f"Field {field} has wrong type: expected {expected_type}, got {type(output[field])}"
        )


def test_error_bound_consistency(output):
    """Verify the error estimate is consistent with the integral value."""
    if abs(output["integral_value"]) > 1e-10:
        relative_error = output["error_estimate"] / abs(output["integral_value"])
        assert relative_error < 0.01, (
            f"Error estimate too large relative to integral: {relative_error:.4f}"
        )


def test_convergence_order_physical(output):
    """Verify convergence order is physically reasonable for Simpson-based methods."""
    order = output["convergence_order"]
    if order > 0:
        assert 2.0 <= order <= 6.0, (
            f"Convergence order {order} outside physical range [2.0, 6.0]"
        )
