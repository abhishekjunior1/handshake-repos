"""
Verification tests for the network flow aggregation pipeline.

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
    """Verify the correct number of flows remain after deduplication."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["summary"]["flows_after_dedup"] == expected["summary"]["flows_after_dedup"], (
        f"Flows after dedup: got {actual['summary']['flows_after_dedup']}, "
        f"expected {expected['summary']['flows_after_dedup']}"
    )


def test_duplicates_removed():
    """Verify the correct number of duplicates were identified and removed."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["summary"]["duplicates_removed"] == expected["summary"]["duplicates_removed"], (
        f"Duplicates removed: got {actual['summary']['duplicates_removed']}, "
        f"expected {expected['summary']['duplicates_removed']}"
    )


def test_bin_count():
    """Verify the correct number of bins were produced."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert len(actual["bins"]) == len(expected["bins"])


def test_bin_flow_counts():
    """Verify the flow count per bin is correct after deduplication."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        assert ab["flow_count"] == eb["flow_count"], (
            f"Bin {i} flow_count: got {ab['flow_count']}, expected {eb['flow_count']}"
        )


def test_bin_total_bytes():
    """Verify the total bytes sum per bin is correct."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        assert approx_equal(ab["total_bytes"], eb["total_bytes"]), (
            f"Bin {i} total_bytes: got {ab['total_bytes']}, expected {eb['total_bytes']}"
        )


def test_per_flow_avg():
    """Verify the per-flow average is computed with correct population size."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        assert approx_equal(ab["per_flow_avg"], eb["per_flow_avg"]), (
            f"Bin {i} per_flow_avg: got {ab['per_flow_avg']}, expected {eb['per_flow_avg']}"
        )


def test_smoothed_utilization():
    """Verify the smoothed utilization baseline is computed correctly."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        assert approx_equal(ab["smoothed_utilization"], eb["smoothed_utilization"]), (
            f"Bin {i} smoothed_utilization: got {ab['smoothed_utilization']}, "
            f"expected {eb['smoothed_utilization']}"
        )


def test_per_prefix_counts():
    """Verify per-prefix flow counts within each bin."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        for prefix in eb["prefix_stats"]:
            assert prefix in ab["prefix_stats"], f"Bin {i}: missing prefix '{prefix}'"
            assert ab["prefix_stats"][prefix]["count"] == eb["prefix_stats"][prefix]["count"], (
                f"Bin {i} prefix '{prefix}' count: got {ab['prefix_stats'][prefix]['count']}, "
                f"expected {eb['prefix_stats'][prefix]['count']}"
            )


def test_per_prefix_bytes():
    """Verify per-prefix total bytes within each bin."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        for prefix in eb["prefix_stats"]:
            assert approx_equal(
                ab["prefix_stats"][prefix]["total_bytes"],
                eb["prefix_stats"][prefix]["total_bytes"]
            ), (
                f"Bin {i} prefix '{prefix}' total_bytes: "
                f"got {ab['prefix_stats'][prefix]['total_bytes']}, "
                f"expected {eb['prefix_stats'][prefix]['total_bytes']}"
            )


def test_population_variance():
    """Verify the population variance is computed with correct population size."""
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    for i, (ab, eb) in enumerate(zip(actual["bins"], expected["bins"])):
        assert approx_equal(ab["variance"], eb["variance"]), (
            f"Bin {i} variance: got {ab['variance']}, expected {eb['variance']}"
        )
