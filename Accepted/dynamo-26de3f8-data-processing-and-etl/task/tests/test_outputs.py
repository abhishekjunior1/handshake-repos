"""
Verification tests for the streaming event processing pipeline.

Compares the agent's output against expected results from a correctly
implemented pipeline run on the hidden test dataset.
"""

import json
import os

EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"


def load_json(path):
    """Load and parse a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4, abs_tol=1e-6):
    """Check if two floating point numbers are approximately equal."""
    if a == b:
        return True
    if a is None or b is None:
        return a == b
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


def test_output_file_exists():
    """Verify that the pipeline produced an output file."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH)


def test_output_is_valid_json():
    """Verify the output file contains valid JSON."""
    try:
        load_json(ACTUAL_OUTPUT_PATH)
    except Exception as e:
        assert False, f"Invalid JSON: {e}"


def test_dedup_count():
    """Verify the correct number of events remain after deduplication."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["summary"]["events_after_dedup"] == expected["summary"]["events_after_dedup"], (
        f"Events after dedup: got {actual['summary']['events_after_dedup']}, "
        f"expected {expected['summary']['events_after_dedup']}"
    )


def test_duplicates_removed():
    """Verify the correct number of duplicates were identified and removed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["summary"]["duplicates_removed"] == expected["summary"]["duplicates_removed"], (
        f"Duplicates removed: got {actual['summary']['duplicates_removed']}, "
        f"expected {expected['summary']['duplicates_removed']}"
    )


def test_window_count():
    """Verify the correct number of windows were produced."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert len(actual["windows"]) == len(expected["windows"])


def test_window_event_counts():
    """Verify the event count per window is correct after deduplication."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (aw, ew) in enumerate(zip(actual["windows"], expected["windows"])):
        assert aw["event_count"] == ew["event_count"], (
            f"Window {i} event_count: got {aw['event_count']}, expected {ew['event_count']}"
        )


def test_window_sums():
    """Verify the value sum per window is correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (aw, ew) in enumerate(zip(actual["windows"], expected["windows"])):
        assert approx_equal(aw["window_sum"], ew["window_sum"]), (
            f"Window {i} window_sum: got {aw['window_sum']}, expected {ew['window_sum']}"
        )


def test_per_key_counts():
    """Verify per-key event counts within each window."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (aw, ew) in enumerate(zip(actual["windows"], expected["windows"])):
        for key in ew["keys"]:
            assert key in aw["keys"], f"Window {i}: missing key '{key}'"
            assert aw["keys"][key]["count"] == ew["keys"][key]["count"], (
                f"Window {i} key '{key}' count: got {aw['keys'][key]['count']}, "
                f"expected {ew['keys'][key]['count']}"
            )


def test_per_key_sums():
    """Verify per-key value sums within each window."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (aw, ew) in enumerate(zip(actual["windows"], expected["windows"])):
        for key in ew["keys"]:
            assert approx_equal(aw["keys"][key]["sum"], ew["keys"][key]["sum"]), (
                f"Window {i} key '{key}' sum: got {aw['keys'][key]['sum']}, "
                f"expected {ew['keys'][key]['sum']}"
            )


def test_running_sums():
    """Verify the running sum with decay carry-forward is computed correctly."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (aw, ew) in enumerate(zip(actual["windows"], expected["windows"])):
        assert approx_equal(aw["running_sum"], ew["running_sum"]), (
            f"Window {i} running_sum: got {aw['running_sum']}, "
            f"expected {ew['running_sum']}"
        )


def test_population_variance():
    """Verify the population variance is computed with correct population size."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (aw, ew) in enumerate(zip(actual["windows"], expected["windows"])):
        assert approx_equal(aw["variance"], ew["variance"]), (
            f"Window {i} variance: got {aw['variance']}, expected {ew['variance']}"
        )
