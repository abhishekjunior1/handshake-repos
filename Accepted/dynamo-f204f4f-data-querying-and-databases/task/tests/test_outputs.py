"""
Verification tests for the query execution plan optimizer.

Compares pipeline output against expected results on hidden database configuration.
"""

import json
import os
import math

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_output():
    """Load the pipeline's output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4):
    """Check approximate equality for floating point values."""
    if a == b:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 1e-6
    return abs(a - b) / max(abs(a), abs(b)) < rel_tol


def test_optimizer_version():
    """Verify the optimizer version string is correct."""
    output = load_output()
    expected = load_expected()
    assert output["optimizer_version"] == expected["optimizer_version"]


def test_plan_count():
    """Verify the correct number of query plans are generated."""
    output = load_output()
    expected = load_expected()
    assert len(output["plans"]) == len(expected["plans"]), \
        f"Expected {len(expected['plans'])} plans, got {len(output['plans'])}"


def test_first_query_output_rows():
    """Verify estimated output rows for the first query reflect correct join cardinality."""
    output = load_output()
    expected = load_expected()
    out_rows = output["plans"][0]["plan_summary"]["estimated_output_rows"]
    exp_rows = expected["plans"][0]["plan_summary"]["estimated_output_rows"]
    assert out_rows == exp_rows, \
        f"Q0 output_rows: expected {exp_rows}, got {out_rows}"


def test_first_query_total_cost():
    """Verify total estimated cost for the first query plan."""
    output = load_output()
    expected = load_expected()
    out_cost = output["plans"][0]["plan_summary"]["total_estimated_cost"]
    exp_cost = expected["plans"][0]["plan_summary"]["total_estimated_cost"]
    assert approx_equal(out_cost, exp_cost), \
        f"Q0 total_cost: expected {exp_cost}, got {out_cost}"


def test_first_query_join_strategy():
    """Verify the join strategy selected for the first query."""
    output = load_output()
    expected = load_expected()
    out_strat = output["plans"][0]["plan_summary"]["join_strategy"]
    exp_strat = expected["plans"][0]["plan_summary"]["join_strategy"]
    assert out_strat == exp_strat, \
        f"Q0 join_strategy: expected {exp_strat}, got {out_strat}"


def test_first_query_access_strategies():
    """Verify table access strategies for the first query."""
    output = load_output()
    expected = load_expected()
    out_access = output["plans"][0]["plan_summary"]["table_access_strategies"]
    exp_access = expected["plans"][0]["plan_summary"]["table_access_strategies"]
    assert out_access == exp_access, \
        f"Q0 access_strategies: expected {exp_access}, got {out_access}"


def test_second_query_output_rows():
    """Verify estimated output rows for the second query."""
    output = load_output()
    expected = load_expected()
    out_rows = output["plans"][1]["plan_summary"]["estimated_output_rows"]
    exp_rows = expected["plans"][1]["plan_summary"]["estimated_output_rows"]
    assert out_rows == exp_rows, \
        f"Q1 output_rows: expected {exp_rows}, got {out_rows}"


def test_second_query_total_cost():
    """Verify total estimated cost for the second query plan."""
    output = load_output()
    expected = load_expected()
    out_cost = output["plans"][1]["plan_summary"]["total_estimated_cost"]
    exp_cost = expected["plans"][1]["plan_summary"]["total_estimated_cost"]
    assert approx_equal(out_cost, exp_cost), \
        f"Q1 total_cost: expected {exp_cost}, got {out_cost}"


def test_second_query_join_strategy():
    """Verify the join strategy selected for the second query."""
    output = load_output()
    expected = load_expected()
    out_strat = output["plans"][1]["plan_summary"]["join_strategy"]
    exp_strat = expected["plans"][1]["plan_summary"]["join_strategy"]
    assert out_strat == exp_strat, \
        f"Q1 join_strategy: expected {exp_strat}, got {out_strat}"


def test_second_query_access_strategies():
    """Verify table access strategies for the second query."""
    output = load_output()
    expected = load_expected()
    out_access = output["plans"][1]["plan_summary"]["table_access_strategies"]
    exp_access = expected["plans"][1]["plan_summary"]["table_access_strategies"]
    assert out_access == exp_access, \
        f"Q1 access_strategies: expected {exp_access}, got {out_access}"


def test_cost_breakdown_first_query():
    """Verify cost breakdown details for the first query."""
    output = load_output()
    expected = load_expected()
    out_cb = output["plans"][0]["cost_breakdown"]
    exp_cb = expected["plans"][0]["cost_breakdown"]
    assert approx_equal(out_cb["total_plan_cost"], exp_cb["total_plan_cost"]), \
        f"Q0 total_plan_cost: expected {exp_cb['total_plan_cost']}, got {out_cb['total_plan_cost']}"


def test_cost_breakdown_second_query():
    """Verify cost breakdown details for the second query."""
    output = load_output()
    expected = load_expected()
    out_cb = output["plans"][1]["cost_breakdown"]
    exp_cb = expected["plans"][1]["cost_breakdown"]
    assert approx_equal(out_cb["total_plan_cost"], exp_cb["total_plan_cost"]), \
        f"Q1 total_plan_cost: expected {exp_cb['total_plan_cost']}, got {out_cb['total_plan_cost']}"


def test_first_query_join_selectivity():
    """Verify join selectivity computation for the first query."""
    output = load_output()
    expected = load_expected()
    out_sel = output["plans"][0]["join_plan"]["join_selectivity"]
    exp_sel = expected["plans"][0]["join_plan"]["join_selectivity"]
    assert approx_equal(out_sel, exp_sel), \
        f"Q0 join_selectivity: expected {exp_sel}, got {out_sel}"


def test_second_query_join_selectivity():
    """Verify join selectivity computation for the second query."""
    output = load_output()
    expected = load_expected()
    out_sel = output["plans"][1]["join_plan"]["join_selectivity"]
    exp_sel = expected["plans"][1]["join_plan"]["join_selectivity"]
    assert approx_equal(out_sel, exp_sel), \
        f"Q1 join_selectivity: expected {exp_sel}, got {out_sel}"


def test_full_output_match():
    """Verify the complete output matches expected (comprehensive check)."""
    output = load_output()
    expected = load_expected()
    assert output == expected, \
        "Full output does not match expected output"
