"""
Tests for the Kubernetes NetworkPolicy evaluation pipeline output.

Compares the pipeline's output against the expected correct evaluation
to verify that all policy ordering, egress default stance, and CIDR
exception handling behaviors are correct.
"""

import json
import os
import pytest


@pytest.fixture
def actual_output():
    """Load the actual pipeline output from /app/output.json."""
    with open("/app/output.json", "r") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected correct output from /app/expected_output.json."""
    with open("/app/expected_output.json", "r") as f:
        return json.load(f)


def test_summary_total_flows(actual_output, expected_output):
    """Verify that the total number of evaluated flows matches expected count."""
    assert actual_output["summary"]["total_flows_evaluated"] == expected_output["summary"]["total_flows_evaluated"]


def test_summary_allowed_count(actual_output, expected_output):
    """Verify that the number of allowed flows matches expected value."""
    assert actual_output["summary"]["allowed"] == expected_output["summary"]["allowed"]


def test_summary_denied_count(actual_output, expected_output):
    """Verify that the number of denied flows matches expected value."""
    assert actual_output["summary"]["denied"] == expected_output["summary"]["denied"]


def test_summary_allow_rate(actual_output, expected_output):
    """Verify that the computed allow rate matches expected ratio."""
    assert actual_output["summary"]["allow_rate"] == expected_output["summary"]["allow_rate"]


def test_evaluation_count(actual_output, expected_output):
    """Verify that the number of evaluation entries matches expected."""
    assert len(actual_output["evaluations"]) == len(expected_output["evaluations"])


def test_flow1_final_verdict(actual_output, expected_output):
    """Verify flow-1 final verdict: monitor-agent to web-app on port 8080."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-1")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-1")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow1_ingress_policy(actual_output, expected_output):
    """Verify flow-1 ingress policy attribution reflects creation-order precedence."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-1")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-1")
    assert actual["ingress_policy"] == expected["ingress_policy"]


def test_flow2_final_verdict(actual_output, expected_output):
    """Verify flow-2 final verdict: api-main to web-app on port 8080."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-2")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-2")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow3_egress_verdict(actual_output, expected_output):
    """Verify flow-3 egress verdict: api-worker egress default when unselected by egress policy."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-3")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-3")
    assert actual["egress_verdict"] == expected["egress_verdict"]


def test_flow3_final_verdict(actual_output, expected_output):
    """Verify flow-3 final verdict: api-worker to db-primary on port 5432."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-3")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-3")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow4_egress_verdict(actual_output, expected_output):
    """Verify flow-4 egress verdict: CIDR except block should deny traffic to 10.0.5.15."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-4")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-4")
    assert actual["egress_verdict"] == expected["egress_verdict"]


def test_flow4_final_verdict(actual_output, expected_output):
    """Verify flow-4 final verdict: traffic to excepted CIDR should be denied."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-4")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-4")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow5_final_verdict(actual_output, expected_output):
    """Verify flow-5 final verdict: api-main to db-primary on port 5432 is allowed."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-5")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-5")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow6_final_verdict(actual_output, expected_output):
    """Verify flow-6 final verdict: web-app to api-main on port 3000 is allowed."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-6")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-6")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow7_final_verdict(actual_output, expected_output):
    """Verify flow-7 final verdict: monitor-agent to api-main on port 9090 is allowed."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-7")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-7")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow8_egress_verdict(actual_output, expected_output):
    """Verify flow-8 egress verdict: db-replica unselected but egress policy exists in namespace."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-8")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-8")
    assert actual["egress_verdict"] == expected["egress_verdict"]


def test_flow8_final_verdict(actual_output, expected_output):
    """Verify flow-8 final verdict: db-replica to api-main on port 3000."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-8")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-8")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow9_egress_verdict(actual_output, expected_output):
    """Verify flow-9 egress verdict: log-collector unselected but egress policy exists in delta."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-9")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-9")
    assert actual["egress_verdict"] == expected["egress_verdict"]


def test_flow9_final_verdict(actual_output, expected_output):
    """Verify flow-9 final verdict: log-collector to api-main on port 3000 is denied."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-9")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-9")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow10_final_verdict(actual_output, expected_output):
    """Verify flow-10 final verdict: api-main to external IP not in except block is allowed."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-10")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-10")
    assert actual["final_verdict"] == expected["final_verdict"]


def test_flow10_egress_verdict(actual_output, expected_output):
    """Verify flow-10 egress verdict: CIDR match without exception allows traffic."""
    actual = next(e for e in actual_output["evaluations"] if e["flow_id"] == "flow-10")
    expected = next(e for e in expected_output["evaluations"] if e["flow_id"] == "flow-10")
    assert actual["egress_verdict"] == expected["egress_verdict"]


def test_connection_stats(actual_output, expected_output):
    """Verify connection tracker statistics match expected values."""
    assert actual_output["connection_stats"] == expected_output["connection_stats"]


def test_full_output_match(actual_output, expected_output):
    """Verify the complete output matches expected output exactly."""
    assert actual_output == expected_output
