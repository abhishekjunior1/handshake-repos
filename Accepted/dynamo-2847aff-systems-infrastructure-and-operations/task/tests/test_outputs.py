"""Tests for zone-based firewall policy evaluation pipeline output correctness."""

import json
import os

import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
OUTPUT_PATH = "/app/output.json"


def load_output():
    """Load the pipeline output from disk."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


def load_expected():
    """Load the expected output for comparison."""
    with open(EXPECTED_OUTPUT_PATH, "r") as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produces an output file at the expected path."""
    assert os.path.exists(OUTPUT_PATH), "output.json was not created"


def test_output_schema_valid():
    """Verify that output.json contains the required top-level keys and structure."""
    output = load_output()
    assert "flow_results" in output, "Missing flow_results key"
    assert "summary" in output, "Missing summary key"
    assert isinstance(output["flow_results"], list), "flow_results must be a list"
    assert isinstance(output["summary"], dict), "summary must be a dict"
    required_summary_keys = ["total_packets", "permitted", "denied", "nat_translations", "stateful_matches"]
    for key in required_summary_keys:
        assert key in output["summary"], f"Missing summary key: {key}"


def test_flow_result_entry_schema():
    """Verify that each flow result entry contains all required fields with correct types."""
    output = load_output()
    required_keys = ["packet_id", "source_zone", "dest_zone", "action", "nat_applied", "connection_state", "matched_rule"]
    for entry in output["flow_results"]:
        for key in required_keys:
            assert key in entry, f"Packet {entry.get('packet_id', '?')} missing key: {key}"
        assert isinstance(entry["packet_id"], int), "packet_id must be int"
        assert isinstance(entry["nat_applied"], bool), "nat_applied must be bool"
        assert entry["action"] in ("permit", "deny"), "action must be permit or deny"
        assert entry["connection_state"] in ("new", "established"), "connection_state must be new or established"


def test_total_packet_count():
    """Verify that the total packet count in summary matches expected value."""
    output = load_output()
    expected = load_expected()
    assert output["summary"]["total_packets"] == expected["summary"]["total_packets"]


def test_permitted_count():
    """Verify that the number of permitted packets matches expected value."""
    output = load_output()
    expected = load_expected()
    assert output["summary"]["permitted"] == expected["summary"]["permitted"], \
        f"Expected {expected['summary']['permitted']} permitted, got {output['summary']['permitted']}"


def test_denied_count():
    """Verify that the number of denied packets matches expected value."""
    output = load_output()
    expected = load_expected()
    assert output["summary"]["denied"] == expected["summary"]["denied"], \
        f"Expected {expected['summary']['denied']} denied, got {output['summary']['denied']}"


def test_nat_translation_count():
    """Verify that the NAT translation count matches expected value."""
    output = load_output()
    expected = load_expected()
    assert output["summary"]["nat_translations"] == expected["summary"]["nat_translations"], \
        f"Expected {expected['summary']['nat_translations']} NAT translations, got {output['summary']['nat_translations']}"


def test_stateful_match_count():
    """Verify that the stateful match count matches expected value."""
    output = load_output()
    expected = load_expected()
    assert output["summary"]["stateful_matches"] == expected["summary"]["stateful_matches"], \
        f"Expected {expected['summary']['stateful_matches']} stateful matches, got {output['summary']['stateful_matches']}"


def test_per_packet_actions():
    """Verify that each packet's action (permit/deny) matches expected values."""
    output = load_output()
    expected = load_expected()
    for i, (result, exp) in enumerate(zip(output["flow_results"], expected["flow_results"])):
        assert result["action"] == exp["action"], \
            f"Packet {result['packet_id']}: expected action '{exp['action']}', got '{result['action']}'"


def test_per_packet_nat_flags():
    """Verify that each packet's NAT application flag matches expected values."""
    output = load_output()
    expected = load_expected()
    for i, (result, exp) in enumerate(zip(output["flow_results"], expected["flow_results"])):
        assert result["nat_applied"] == exp["nat_applied"], \
            f"Packet {result['packet_id']}: expected nat_applied={exp['nat_applied']}, got {result['nat_applied']}"


def test_per_packet_connection_state():
    """Verify that each packet's connection state matches expected values."""
    output = load_output()
    expected = load_expected()
    for i, (result, exp) in enumerate(zip(output["flow_results"], expected["flow_results"])):
        assert result["connection_state"] == exp["connection_state"], \
            f"Packet {result['packet_id']}: expected state '{exp['connection_state']}', got '{result['connection_state']}'"


def test_per_packet_matched_rules():
    """Verify that each packet's matched rule name matches expected values."""
    output = load_output()
    expected = load_expected()
    for i, (result, exp) in enumerate(zip(output["flow_results"], expected["flow_results"])):
        assert result["matched_rule"] == exp["matched_rule"], \
            f"Packet {result['packet_id']}: expected rule '{exp['matched_rule']}', got '{result['matched_rule']}'"


def test_full_output_match():
    """Verify that the complete output matches expected output exactly."""
    output = load_output()
    expected = load_expected()
    assert output == expected, "Full output does not match expected output"
