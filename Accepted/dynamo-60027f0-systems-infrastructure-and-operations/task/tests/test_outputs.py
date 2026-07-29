"""Tests for network packet processing pipeline output.

Validates that the pipeline produces correct forwarding decisions
including NAT translation, firewall policy, routing, QoS marking,
and load balancer assignment for all packet types.
"""

import json
import pytest
from pathlib import Path


EXPECTED_PATH = Path("/tests/expected_output.json")
OUTPUT_PATH = Path("/app/output.json")


@pytest.fixture
def output():
    """Load the pipeline output for verification."""
    assert OUTPUT_PATH.exists(), f"Output file not found: {OUTPUT_PATH}"
    with open(OUTPUT_PATH) as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Load the expected output for comparison."""
    assert EXPECTED_PATH.exists(), f"Expected output not found: {EXPECTED_PATH}"
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def test_output_structure(output):
    """Verify the output contains a results array with correct count."""
    assert "results" in output, "Output missing 'results' key"
    assert len(output["results"]) == 4, (
        f"Expected 4 results, got {len(output['results'])}"
    )


def test_packet_statuses(output, expected):
    """Verify all packets reach their correct final status."""
    for i in range(len(expected["results"])):
        result = output["results"][i]
        exp = expected["results"][i]
        assert result["status"] == exp["status"], (
            f"Packet {i+1}: status '{result['status']}', "
            f"expected '{exp['status']}'"
        )


def test_nat_translation(output, expected):
    """Verify NAT correctly translates destination addresses."""
    for i in range(len(expected["results"])):
        result = output["results"][i]
        exp = expected["results"][i]
        if "nat" in exp:
            assert result.get("nat") == exp["nat"], (
                f"Packet {i+1} NAT mismatch: {result.get('nat')} "
                f"vs {exp['nat']}"
            )


def test_firewall_decisions(output, expected):
    """Verify firewall evaluates against correct addresses."""
    for i in range(len(expected["results"])):
        result = output["results"][i]
        exp = expected["results"][i]
        if "firewall" in exp:
            assert result["firewall"]["action"] == exp["firewall"]["action"], (
                f"Packet {i+1}: firewall '{result['firewall']['action']}', "
                f"expected '{exp['firewall']['action']}'"
            )
            assert result["firewall"]["matched_rule"] == exp["firewall"]["matched_rule"], (
                f"Packet {i+1}: rule {result['firewall']['matched_rule']}, "
                f"expected {exp['firewall']['matched_rule']}"
            )


def test_routing_decisions(output, expected):
    """Verify routing selects correct next-hop for each packet."""
    for i in range(len(expected["results"])):
        result = output["results"][i]
        exp = expected["results"][i]
        if "routing" in exp:
            assert result["routing"]["next_hop"] == exp["routing"]["next_hop"], (
                f"Packet {i+1}: next_hop '{result['routing']['next_hop']}', "
                f"expected '{exp['routing']['next_hop']}'"
            )


def test_qos_classification(output, expected):
    """Verify QoS applies correct per-hop behavior marking."""
    for i in range(len(expected["results"])):
        result = output["results"][i]
        exp = expected["results"][i]
        if "qos" in exp:
            assert result.get("qos") == exp["qos"], (
                f"Packet {i+1} QoS mismatch"
            )


def test_load_balancer(output, expected):
    """Verify load balancer assigns correct backend via consistent hashing."""
    for i in range(len(expected["results"])):
        result = output["results"][i]
        exp = expected["results"][i]
        if "load_balancer" in exp:
            assert result["load_balancer"]["backend"] == exp["load_balancer"]["backend"], (
                f"Packet {i+1}: LB '{result['load_balancer']['backend']}', "
                f"expected '{exp['load_balancer']['backend']}'"
            )


def test_ttl_expiry(output, expected):
    """Verify packets with expired TTL are correctly dropped."""
    for i in range(len(expected["results"])):
        exp = expected["results"][i]
        if exp["status"] == "dropped":
            result = output["results"][i]
            assert result["status"] == "dropped", (
                f"Packet {i+1} should be dropped (TTL expired)"
            )
            assert result["routing"]["status"] == "ttl_expired"


def test_full_output_match(output, expected):
    """Verify complete pipeline output matches expected results exactly."""
    assert output == expected, "Full output does not match expected results"
