"""
Verification tests for the type inference pipeline on hidden configuration 1.
Checks that all output fields match the expected results from correct inference.
"""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_output():
    """Load the pipeline output from /app/output.json."""
    with open("/app/output.json", "r") as f:
        return json.load(f)


def load_expected():
    """Load the expected output from tests directory."""
    with open(os.path.join(TESTS_DIR, "expected_output.json"), "r") as f:
        return json.load(f)


def test_status_is_success():
    """Verify that type inference completes successfully."""
    output = load_output()
    expected = load_expected()
    assert output["status"] == expected["status"], (
        f"Expected status '{expected['status']}', got '{output['status']}'"
    )


def test_inferred_type_matches():
    """Verify the top-level inferred type is correct."""
    output = load_output()
    expected = load_expected()
    assert output["inferred_type"] == expected["inferred_type"], (
        f"Expected inferred_type '{expected['inferred_type']}', got '{output['inferred_type']}'"
    )


def test_substitution_matches():
    """Verify the unification substitution contains correct type mappings."""
    output = load_output()
    expected = load_expected()
    assert output["substitution"] == expected["substitution"], (
        f"Substitution mismatch:\n  Expected: {expected['substitution']}\n  Got: {output['substitution']}"
    )


def test_constraints_count():
    """Verify the number of generated constraints matches expected."""
    output = load_output()
    expected = load_expected()
    assert output["constraints_generated"] == expected["constraints_generated"], (
        f"Expected {expected['constraints_generated']} constraints, got {output['constraints_generated']}"
    )


def test_bindings_match():
    """Verify let-binding types are correctly resolved through substitution."""
    output = load_output()
    expected = load_expected()
    assert output["bindings"] == expected["bindings"], (
        f"Bindings mismatch:\n  Expected: {expected['bindings']}\n  Got: {output['bindings']}"
    )


def test_generalized_types_match():
    """Verify generalized type schemes for polymorphic let-bindings."""
    output = load_output()
    expected = load_expected()
    assert output["generalized_types"] == expected["generalized_types"], (
        f"Generalized types mismatch:\n  Expected: {expected['generalized_types']}\n  Got: {output['generalized_types']}"
    )


def test_no_error():
    """Verify no error was reported during inference."""
    output = load_output()
    assert output["error"] is None, f"Unexpected error: {output['error']}"
