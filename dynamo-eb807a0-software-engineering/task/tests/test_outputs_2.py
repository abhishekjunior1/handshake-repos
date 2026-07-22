"""
Verification tests for the type inference pipeline on hidden configuration 2.
Checks all output fields against expected results for a different program structure.
"""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_output():
    """Load the pipeline output from /app/output.json."""
    with open("/app/output.json", "r") as f:
        return json.load(f)


def load_expected():
    """Load the expected output for config 2 from tests directory."""
    with open(os.path.join(TESTS_DIR, "expected_output_2.json"), "r") as f:
        return json.load(f)


def test_status_is_success():
    """Verify type inference succeeds on the higher-order program."""
    output = load_output()
    expected = load_expected()
    assert output["status"] == expected["status"], (
        f"Expected status '{expected['status']}', got '{output['status']}'"
    )


def test_inferred_type_matches():
    """Verify the top-level type for the composed expression."""
    output = load_output()
    expected = load_expected()
    assert output["inferred_type"] == expected["inferred_type"], (
        f"Expected inferred_type '{expected['inferred_type']}', got '{output['inferred_type']}'"
    )


def test_substitution_matches():
    """Verify substitution includes correct arrow-type mappings for higher-order functions."""
    output = load_output()
    expected = load_expected()
    assert output["substitution"] == expected["substitution"], (
        f"Substitution mismatch:\n  Expected: {expected['substitution']}\n  Got: {output['substitution']}"
    )


def test_constraints_count():
    """Verify the constraint count for the multi-application program."""
    output = load_output()
    expected = load_expected()
    assert output["constraints_generated"] == expected["constraints_generated"], (
        f"Expected {expected['constraints_generated']} constraints, got {output['constraints_generated']}"
    )


def test_bindings_match():
    """Verify binding types are fully resolved for higher-order let-bindings."""
    output = load_output()
    expected = load_expected()
    assert output["bindings"] == expected["bindings"], (
        f"Bindings mismatch:\n  Expected: {expected['bindings']}\n  Got: {output['bindings']}"
    )


def test_generalized_types_match():
    """Verify generalized type schemes for the choose function."""
    output = load_output()
    expected = load_expected()
    assert output["generalized_types"] == expected["generalized_types"], (
        f"Generalized types mismatch:\n  Expected: {expected['generalized_types']}\n  Got: {output['generalized_types']}"
    )


def test_no_error():
    """Verify no error reported during higher-order type inference."""
    output = load_output()
    assert output["error"] is None, f"Unexpected error: {output['error']}"
