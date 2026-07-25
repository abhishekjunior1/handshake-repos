"""
Test suite for second hidden configuration verification.
Exercises transitive interpolation chains, include_prefixes filtering,
and multiline value handling with different data patterns.
"""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output_2.json")
OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def expected_output():
    """Load the expected output JSON."""
    with open(EXPECTED_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output JSON."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


def test_full_output_match(actual_output, expected_output):
    """Verify the complete pipeline output matches expected results exactly."""
    assert actual_output == expected_output


def test_transitive_interpolation(actual_output, expected_output):
    """Verify transitive variable chains resolve completely (A->B->C)."""
    env = actual_output["environment"]
    exp = expected_output["environment"]
    assert env.get("LOG_DIR") == exp["LOG_DIR"]
    assert "${" not in env.get("LOG_DIR", ""), "LOG_DIR has unresolved reference"


def test_multiline_startup_msg(actual_output, expected_output):
    """Verify multiline value uses actual newlines not literal backslash-n."""
    env = actual_output["environment"]
    exp = expected_output["environment"]
    assert env.get("STARTUP_MSG") == exp["STARTUP_MSG"]
    assert "\n" in env.get("STARTUP_MSG", ""), "STARTUP_MSG should have real newlines"


def test_quote_boundary_handling(actual_output, expected_output):
    """Verify double-boundary quotes strip only one pair."""
    env = actual_output["environment"]
    exp = expected_output["environment"]
    assert env.get("BINDING") == exp["BINDING"]
    assert env.get("CERT_SUBJECT") == exp["CERT_SUBJECT"]


def test_include_prefixes_filtering(actual_output, expected_output):
    """Verify include_prefixes correctly limits exported variables."""
    env = actual_output["environment"]
    exp = expected_output["environment"]
    assert set(env.keys()) == set(exp.keys())


def test_environment_sorted(actual_output, expected_output):
    """Verify environment keys are in sorted order."""
    keys = list(actual_output["environment"].keys())
    assert keys == sorted(keys)
