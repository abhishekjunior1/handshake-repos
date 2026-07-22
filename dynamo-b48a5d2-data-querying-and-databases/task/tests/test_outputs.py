"""Tests for the analytical query engine pipeline output.

Compares the pipeline output against expected results for correctness.
Each test validates a specific query's output structure and values.
"""

import json
import os
import pytest

OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = "/tests/expected_output.json"


@pytest.fixture(scope="module")
def output_data():
    """Load the pipeline output from output.json."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


@pytest.fixture(scope="module")
def expected_data():
    """Load the expected output for comparison."""
    with open(EXPECTED_PATH, "r") as f:
        return json.load(f)


def _get_result_by_id(results, query_id):
    """Helper to find a query result by its ID."""
    for result in results:
        if result["query_id"] == query_id:
            return result
    return None


class TestOutputStructure:
    """Tests for overall output structure and metadata."""

    def test_output_has_metadata(self, output_data):
        """Verify output contains metadata section with required fields."""
        assert "metadata" in output_data
        assert "query_count" in output_data["metadata"]
        assert "engine_version" in output_data["metadata"]

    def test_output_has_results(self, output_data):
        """Verify output contains results array."""
        assert "results" in output_data
        assert isinstance(output_data["results"], list)

    def test_query_count_matches(self, output_data, expected_data):
        """Verify the number of executed queries matches expected."""
        assert output_data["metadata"]["query_count"] == expected_data["metadata"]["query_count"]


class TestProductSummary:
    """Tests for the product_summary query (join-aggregate)."""

    def test_row_count(self, output_data, expected_data):
        """Verify product_summary returns the correct number of groups."""
        actual = _get_result_by_id(output_data["results"], "product_summary")
        expected = _get_result_by_id(expected_data["results"], "product_summary")
        assert actual is not None, "product_summary query not found in output"
        assert actual["row_count"] == expected["row_count"]

    def test_order_counts(self, output_data, expected_data):
        """Verify order counts per customer are not inflated by join fan-out."""
        actual = _get_result_by_id(output_data["results"], "product_summary")
        expected = _get_result_by_id(expected_data["results"], "product_summary")
        actual_rows = sorted(actual["rows"], key=lambda r: r["l_customer_id"])
        expected_rows = sorted(expected["rows"], key=lambda r: r["l_customer_id"])
        for act, exp in zip(actual_rows, expected_rows):
            assert act["order_count"] == exp["order_count"], (
                f"Customer {act['l_customer_id']}: expected order_count="
                f"{exp['order_count']}, got {act['order_count']}"
            )

    def test_total_revenue(self, output_data, expected_data):
        """Verify revenue totals are not inflated by join fan-out duplication."""
        actual = _get_result_by_id(output_data["results"], "product_summary")
        expected = _get_result_by_id(expected_data["results"], "product_summary")
        actual_rows = sorted(actual["rows"], key=lambda r: r["l_customer_id"])
        expected_rows = sorted(expected["rows"], key=lambda r: r["l_customer_id"])
        for act, exp in zip(actual_rows, expected_rows):
            assert act["total_revenue"] == pytest.approx(exp["total_revenue"]), (
                f"Customer {act['l_customer_id']}: expected total_revenue="
                f"{exp['total_revenue']}, got {act['total_revenue']}"
            )


class TestCustomerRunningTotal:
    """Tests for the customer_running_total query (window function)."""

    def test_row_count(self, output_data, expected_data):
        """Verify all orders are included in the running total output."""
        actual = _get_result_by_id(output_data["results"], "customer_running_total")
        expected = _get_result_by_id(expected_data["results"], "customer_running_total")
        assert actual is not None, "customer_running_total query not found in output"
        assert actual["row_count"] == expected["row_count"]

    def test_cumulative_amounts(self, output_data, expected_data):
        """Verify running totals accumulate correctly row by row."""
        actual = _get_result_by_id(output_data["results"], "customer_running_total")
        expected = _get_result_by_id(expected_data["results"], "customer_running_total")
        actual_rows = actual["rows"]
        expected_rows = expected["rows"]
        for i, (act, exp) in enumerate(zip(actual_rows, expected_rows)):
            assert act["cumulative_amount"] == pytest.approx(exp["cumulative_amount"]), (
                f"Row {i} (order_id={act.get('order_id')}): expected "
                f"cumulative_amount={exp['cumulative_amount']}, got {act['cumulative_amount']}"
            )

    def test_first_row_per_partition(self, output_data, expected_data):
        """Verify the first row in each partition equals its own amount."""
        actual = _get_result_by_id(output_data["results"], "customer_running_total")
        expected = _get_result_by_id(expected_data["results"], "customer_running_total")
        actual_rows = actual["rows"]
        expected_rows = expected["rows"]
        seen_customers = set()
        for act, exp in zip(actual_rows, expected_rows):
            cust = act["customer_id"]
            if cust not in seen_customers:
                seen_customers.add(cust)
                assert act["cumulative_amount"] == pytest.approx(act["amount"]), (
                    f"First row for customer {cust}: cumulative_amount should equal "
                    f"amount ({act['amount']}), got {act['cumulative_amount']}"
                )


class TestCustomerOrderCount:
    """Tests for the customer_order_count query (LEFT JOIN with filter)."""

    def test_row_count(self, output_data, expected_data):
        """Verify all customers are present in the output including those with no orders."""
        actual = _get_result_by_id(output_data["results"], "customer_order_count")
        expected = _get_result_by_id(expected_data["results"], "customer_order_count")
        assert actual is not None, "customer_order_count query not found in output"
        assert actual["row_count"] == expected["row_count"], (
            f"Expected {expected['row_count']} customers, got {actual['row_count']}. "
            f"All customers should be preserved in LEFT JOIN results."
        )

    def test_completed_order_counts(self, output_data, expected_data):
        """Verify completed order counts are correct for each customer."""
        actual = _get_result_by_id(output_data["results"], "customer_order_count")
        expected = _get_result_by_id(expected_data["results"], "customer_order_count")
        actual_rows = sorted(actual["rows"], key=lambda r: r["l_customer_name"])
        expected_rows = sorted(expected["rows"], key=lambda r: r["l_customer_name"])
        for act, exp in zip(actual_rows, expected_rows):
            assert act["completed_orders"] == exp["completed_orders"], (
                f"Customer '{act['l_customer_name']}': expected completed_orders="
                f"{exp['completed_orders']}, got {act['completed_orders']}"
            )

    def test_customers_with_no_orders_preserved(self, output_data, expected_data):
        """Verify customers with no matching orders appear with zero count."""
        actual = _get_result_by_id(output_data["results"], "customer_order_count")
        expected = _get_result_by_id(expected_data["results"], "customer_order_count")
        expected_names = {r["l_customer_name"] for r in expected["rows"]}
        actual_names = {r["l_customer_name"] for r in actual["rows"]}
        missing = expected_names - actual_names
        assert not missing, (
            f"Customers missing from output: {missing}. "
            f"LEFT JOIN should preserve all left-side rows."
        )
