"""
Test validation for the polynomial GCD computation pipeline.

Loads the pipeline output from /app/output.json and compares against
the expected output to verify correctness of GCD, resultant, and
factorization computations.
"""

import json
import os
import pytest


ACTUAL_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(os.path.dirname(__file__), "expected_output.json")


@pytest.fixture(scope="module")
def actual_output():
    """Load the actual pipeline output."""
    with open(ACTUAL_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_output():
    """Load the expected pipeline output."""
    with open(EXPECTED_PATH, 'r') as f:
        return json.load(f)


def test_gcd_coefficients(actual_output, expected_output):
    """Verify that the computed GCD has the correct coefficients."""
    actual = actual_output["gcd"]["coefficients"]
    expected = expected_output["gcd"]["coefficients"]
    assert actual == expected, (
        f"GCD coefficients mismatch: got {actual}, expected {expected}"
    )


def test_gcd_degree(actual_output, expected_output):
    """Verify that the computed GCD has the correct degree."""
    actual = actual_output["gcd"]["degree"]
    expected = expected_output["gcd"]["degree"]
    assert actual == expected, (
        f"GCD degree mismatch: got {actual}, expected {expected}"
    )


def test_gcd_leading_coefficient(actual_output, expected_output):
    """Verify that the GCD leading coefficient is correct."""
    actual = actual_output["gcd"]["leading_coefficient"]
    expected = expected_output["gcd"]["leading_coefficient"]
    assert actual == expected, (
        f"Leading coefficient mismatch: got {actual}, expected {expected}"
    )


def test_gcd_verified(actual_output, expected_output):
    """Verify that the GCD passes trial division verification."""
    assert actual_output["gcd"]["verified"] is True, (
        "GCD not verified by trial division"
    )


def test_resultant_value(actual_output, expected_output):
    """Verify the resultant value of the input polynomials."""
    actual = actual_output["resultant"]["value"]
    expected = expected_output["resultant"]["value"]
    assert actual == expected, (
        f"resultant value mismatch: got {actual}, expected {expected}"
    )


def test_subresultant_degrees(actual_output, expected_output):
    """Verify the degree sequence of the subresultant PRS."""
    actual = actual_output["resultant"]["subresultant_degrees"]
    expected = expected_output["resultant"]["subresultant_degrees"]
    assert actual == expected, (
        f"subresultant_degrees mismatch: got {actual}, expected {expected}"
    )


def test_cofactor_resultant(actual_output, expected_output):
    """Verify the resultant of the cofactors f/gcd and g/gcd."""
    actual = actual_output["resultant"]["cofactor_resultant"]
    expected = expected_output["resultant"]["cofactor_resultant"]
    assert actual == expected, (
        f"cofactor_resultant mismatch: got {actual}, expected {expected}"
    )


def test_content_f(actual_output, expected_output):
    """Verify that the content of polynomial f is correctly computed."""
    actual = actual_output["factorization"]["content_f"]
    expected = expected_output["factorization"]["content_f"]
    assert actual == expected, (
        f"content_f mismatch: got {actual}, expected {expected}"
    )


def test_content_g(actual_output, expected_output):
    """Verify that the content of polynomial g is correctly computed."""
    actual = actual_output["factorization"]["content_g"]
    expected = expected_output["factorization"]["content_g"]
    assert actual == expected, (
        f"content_g mismatch: got {actual}, expected {expected}"
    )


def test_content_gcd(actual_output, expected_output):
    """Verify that the content GCD is correctly computed."""
    actual = actual_output["factorization"]["content_gcd"]
    expected = expected_output["factorization"]["content_gcd"]
    assert actual == expected, (
        f"content_gcd mismatch: got {actual}, expected {expected}"
    )


def test_primitive_gcd(actual_output, expected_output):
    """Verify that the primitive part of the GCD is correct."""
    actual = actual_output["factorization"]["primitive_gcd"]
    expected = expected_output["factorization"]["primitive_gcd"]
    assert actual == expected, (
        f"primitive_gcd mismatch: got {actual}, expected {expected}"
    )


def test_square_free_gcd(actual_output, expected_output):
    """Verify the square-free decomposition of the GCD."""
    actual = actual_output["factorization"]["square_free_gcd"]
    expected = expected_output["factorization"]["square_free_gcd"]
    assert actual == expected, (
        f"square_free_gcd mismatch: got {actual}, expected {expected}"
    )


def test_coprime_flag(actual_output, expected_output):
    """Verify that the coprimality flag is correct."""
    actual = actual_output["factorization"]["coprime"]
    expected = expected_output["factorization"]["coprime"]
    assert actual == expected, (
        f"coprime flag mismatch: got {actual}, expected {expected}"
    )


def test_algorithm_metadata(actual_output, expected_output):
    """Verify that the algorithm field in metadata is correct."""
    actual = actual_output["computation_metadata"]["algorithm"]
    expected = expected_output["computation_metadata"]["algorithm"]
    assert actual == expected, (
        f"algorithm mismatch: got {actual}, expected {expected}"
    )


def test_gcd_degree_metadata(actual_output, expected_output):
    """Verify that the GCD degree in metadata is correct."""
    actual = actual_output["computation_metadata"]["gcd_degree"]
    expected = expected_output["computation_metadata"]["gcd_degree"]
    assert actual == expected, (
        f"metadata gcd_degree mismatch: got {actual}, expected {expected}"
    )
