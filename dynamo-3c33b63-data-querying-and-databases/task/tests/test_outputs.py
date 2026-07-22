"""Pytest test suite for the analytical query engine pipeline.

Verifies query results against expected output for join-aggregate queries,
window function queries, and outer-join aggregate queries.
"""

import json
import os

import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def expected_output():
    """Load the expected output from the test fixtures."""
    with open(EXPECTED_OUTPUT_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual output produced by the pipeline."""
    with open(ACTUAL_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produced an output file at the expected path."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH), (
        f"Output file not found at {ACTUAL_OUTPUT_PATH}"
    )


def test_output_is_valid_json(actual_output):
    """Verify that the output file contains valid JSON with required structure."""
    assert "metadata" in actual_output, "Output missing 'metadata' key"
    assert "results" in actual_output, "Output missing 'results' key"
    assert isinstance(actual_output["results"], list), "Results must be a list"


def test_query_count(actual_output, expected_output):
    """Verify that the pipeline executed the correct number of queries."""
    assert len(actual_output["results"]) == len(expected_output["results"]), (
        f"Expected {len(expected_output['results'])} query results, "
        f"got {len(actual_output['results'])}"
    )


def test_join_aggregate_row_count(actual_output, expected_output):
    """Verify the join-aggregate query returns correct number of customer groups.

    The aggregate should reflect the actual number of orders per customer
    without inflation from one-to-many relationships in joined tables.
    """
    expected = expected_output["results"][0]
    actual = actual_output["results"][0]
    assert actual["row_count"] == expected["row_count"], (
        f"Join-aggregate query: expected {expected['row_count']} rows, "
        f"got {actual['row_count']}"
    )


def test_join_aggregate_values(actual_output, expected_output):
    """Verify that aggregate values (counts, sums) are not inflated by fan-out.

    When aggregating after a one-to-many join, measures from the 'one' side
    must reflect their true cardinality, not the expanded cardinality.
    """
    expected_rows = expected_output["results"][0]["rows"]
    actual_rows = actual_output["results"][0]["rows"]

    for i, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
        for key in expected:
            assert actual.get(key) == expected[key], (
                f"Join-aggregate row {i}, column '{key}': "
                f"expected {expected[key]}, got {actual.get(key)}"
            )


def test_window_running_total_values(actual_output, expected_output):
    """Verify running total window function produces correct sequential values.

    The cumulative freight should accumulate row-by-row in partition order,
    not include peer rows that share the same ORDER BY value.
    """
    expected_rows = expected_output["results"][1]["rows"]
    actual_rows = actual_output["results"][1]["rows"]

    assert len(actual_rows) == len(expected_rows), (
        f"Window query row count: expected {len(expected_rows)}, got {len(actual_rows)}"
    )

    for i, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
        assert actual.get("cumulative_freight") == expected.get("cumulative_freight"), (
            f"Window row {i}: cumulative_freight expected "
            f"{expected.get('cumulative_freight')}, got {actual.get('cumulative_freight')}"
        )


def test_window_row_order(actual_output, expected_output):
    """Verify that window query rows maintain correct partition and sort order."""
    expected_rows = expected_output["results"][1]["rows"]
    actual_rows = actual_output["results"][1]["rows"]

    for i, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
        assert actual.get("order_id") == expected.get("order_id"), (
            f"Window row {i}: order_id expected "
            f"{expected.get('order_id')}, got {actual.get('order_id')}"
        )


def test_outer_join_aggregate_row_count(actual_output, expected_output):
    """Verify the outer-join aggregate preserves all customers from left table.

    A LEFT JOIN should retain all customers regardless of whether they have
    matching orders satisfying the filter condition.
    """
    expected = expected_output["results"][2]
    actual = actual_output["results"][2]
    assert actual["row_count"] == expected["row_count"], (
        f"Outer-join aggregate: expected {expected['row_count']} rows, "
        f"got {actual['row_count']}"
    )


def test_outer_join_aggregate_values(actual_output, expected_output):
    """Verify that customers without matching orders show count=0 and NULL totals.

    Customers whose orders don't satisfy the join filter should still appear
    in the result with zero counts and NULL sums, not be excluded entirely.
    """
    expected_rows = expected_output["results"][2]["rows"]
    actual_rows = actual_output["results"][2]["rows"]

    for i, (actual, expected) in enumerate(zip(actual_rows, expected_rows)):
        for key in expected:
            assert actual.get(key) == expected[key], (
                f"Outer-join row {i}, column '{key}': "
                f"expected {expected[key]}, got {actual.get(key)}"
            )


def test_metadata_structure(actual_output, expected_output):
    """Verify that the output metadata contains correct table information."""
    actual_meta = actual_output["metadata"]
    expected_meta = expected_output["metadata"]

    assert actual_meta["query_count"] == expected_meta["query_count"], (
        "Query count mismatch in metadata"
    )
    assert set(actual_meta["tables_loaded"]) == set(expected_meta["tables_loaded"]), (
        "Tables loaded mismatch"
    )
