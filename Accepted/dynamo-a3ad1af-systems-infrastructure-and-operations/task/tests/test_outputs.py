"""
Verification tests for the network configuration validation and routing pipeline.
Tests run against hidden topology and configuration data to verify correctness.
"""

import json
import subprocess
import shutil
import os

import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"
HIDDEN_TOPOLOGY_PATH = "/tests/hidden_topology.json"
HIDDEN_CONFIG_PATH = "/tests/hidden_config.json"


@pytest.fixture(autouse=True)
def run_pipeline():
    """Copy hidden data and run the pipeline before tests execute."""
    # Copy hidden topology to /app
    shutil.copy(HIDDEN_TOPOLOGY_PATH, "/app/hidden_topology.json")
    # Copy hidden config to /app (overwriting visible config)
    shutil.copy(HIDDEN_CONFIG_PATH, "/app/config.json")
    # Run pipeline
    result = subprocess.run(
        ["python3", "/app/pipeline.py", "/app/config.json", "/app/output.json"],
        cwd="/app",
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"


def load_json(path):
    """Load a JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produces an output.json file at the expected path."""
    assert os.path.exists(ACTUAL_OUTPUT_PATH), "output.json not produced"


def test_ospf_link_costs():
    """Verify OSPF link costs are computed correctly using link bandwidth.

    Correct cost formula: reference_bandwidth / link_bandwidth (integer division).
    With reference_bandwidth=100000 and varied link bandwidths (40000, 10000, 20000, 5000),
    the costs should be 2, 10, 5, and 20 respectively.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    actual_costs = actual["routing_analysis"]["ospf_link_costs"]
    expected_costs = expected["routing_analysis"]["ospf_link_costs"]
    assert actual_costs == expected_costs, (
        f"OSPF costs mismatch: got {actual_costs}, expected {expected_costs}"
    )


def test_routing_table_metrics():
    """Verify that routing table metrics reflect correct OSPF costs.

    Route metrics are the sum of link costs along the shortest path.
    Incorrect OSPF costs propagate into wrong route metrics throughout
    the routing tables.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    actual_tables = actual["routing_analysis"]["routing_tables"]
    expected_tables = expected["routing_analysis"]["routing_tables"]

    for router_id in expected_tables:
        assert router_id in actual_tables, f"Missing routing table for {router_id}"
        actual_routes = {
            (r["destination"], r["prefix_length"]): r["metric"]
            for r in actual_tables[router_id]
        }
        expected_routes = {
            (r["destination"], r["prefix_length"]): r["metric"]
            for r in expected_tables[router_id]
        }
        for key, exp_metric in expected_routes.items():
            assert key in actual_routes, f"Missing route {key} in {router_id}"
            assert actual_routes[key] == exp_metric, (
                f"Route metric mismatch for {router_id} -> {key}: "
                f"got {actual_routes[key]}, expected {exp_metric}"
            )


def test_acl_flow_decisions():
    """Verify ACL evaluation produces correct permit/deny decisions for each flow.

    The interface_scope resolution must use the flow's destination address
    (as a /32 host route) rather than the receiving interface's full subnet.
    Incorrect scope resolution causes flows to be incorrectly denied or permitted.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    actual_decisions = actual["acl_evaluation"]["flow_decisions"]
    expected_decisions = expected["acl_evaluation"]["flow_decisions"]

    assert len(actual_decisions) == len(expected_decisions), (
        f"Flow count mismatch: got {len(actual_decisions)}, expected {len(expected_decisions)}"
    )

    for act, exp in zip(actual_decisions, expected_decisions):
        assert act["flow_id"] == exp["flow_id"]
        assert act["action"] == exp["action"], (
            f"Flow {act['flow_id']}: got action '{act['action']}', "
            f"expected '{exp['action']}'"
        )
        assert act["matched_rule"] == exp["matched_rule"], (
            f"Flow {act['flow_id']}: matched rule '{act['matched_rule']}', "
            f"expected '{exp['matched_rule']}'"
        )


def test_acl_permit_deny_counts():
    """Verify the aggregate permit and deny counts match expected values.

    This catches cases where individual flow decisions might be reordered
    but the overall security posture is wrong.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    assert actual["acl_evaluation"]["flows_permitted"] == expected["acl_evaluation"]["flows_permitted"], (
        f"Permitted count: got {actual['acl_evaluation']['flows_permitted']}, "
        f"expected {expected['acl_evaluation']['flows_permitted']}"
    )
    assert actual["acl_evaluation"]["flows_denied"] == expected["acl_evaluation"]["flows_denied"], (
        f"Denied count: got {actual['acl_evaluation']['flows_denied']}, "
        f"expected {expected['acl_evaluation']['flows_denied']}"
    )


def test_summary_fields():
    """Verify the audit report summary contains correct aggregate statistics.

    The summary reflects the overall network health assessment including
    router count, link count, route count, and security posture.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)
    actual_summary = actual["summary"]
    expected_summary = expected["summary"]

    assert actual_summary["total_routers"] == expected_summary["total_routers"]
    assert actual_summary["total_links"] == expected_summary["total_links"]
    assert actual_summary["total_routes_computed"] == expected_summary["total_routes_computed"]
    assert actual_summary["flows_permitted"] == expected_summary["flows_permitted"]
    assert actual_summary["flows_denied"] == expected_summary["flows_denied"]


def test_misconfiguration_detection():
    """Verify misconfiguration detection identifies expected issues.

    The MTU mismatch between R2:eth1 (9000) and R3:eth1 (1500) must be
    detected regardless of OSPF cost computation.
    """
    actual = load_json(ACTUAL_OUTPUT_PATH)
    expected = load_json(EXPECTED_OUTPUT_PATH)

    actual_misconfigs = actual["misconfiguration_report"]
    expected_misconfigs = expected["misconfiguration_report"]

    assert actual_misconfigs["total_issues"] == expected_misconfigs["total_issues"], (
        f"Total issues: got {actual_misconfigs['total_issues']}, "
        f"expected {expected_misconfigs['total_issues']}"
    )
    assert len(actual_misconfigs["mtu_mismatches"]) == len(expected_misconfigs["mtu_mismatches"]), (
        f"MTU mismatches: got {len(actual_misconfigs['mtu_mismatches'])}, "
        f"expected {len(expected_misconfigs['mtu_mismatches'])}"
    )
