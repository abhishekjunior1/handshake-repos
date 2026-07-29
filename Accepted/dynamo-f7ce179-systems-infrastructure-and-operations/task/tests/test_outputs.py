"""
Test suite for service mesh traffic routing pipeline outputs.

Validates that the pipeline produces correct routing decisions when
processing the hidden mesh configuration with multiple services,
backends, circuit breaker states, and health check conditions.
"""

import json
import os
import pytest


EXPECTED_PATH = "/app/expected_output.json"
OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def expected_output():
    """Load the expected pipeline output for comparison."""
    with open(EXPECTED_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output produced during test execution."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produced an output.json file."""
    assert os.path.exists(OUTPUT_PATH), (
        f"Pipeline output file not found at {OUTPUT_PATH}"
    )


def test_pipeline_version(actual_output, expected_output):
    """Verify the pipeline version string matches expected."""
    assert actual_output["pipeline_version"] == expected_output["pipeline_version"], (
        "Pipeline version mismatch"
    )


def test_total_request_count(actual_output, expected_output):
    """Verify that all requests were processed by the pipeline."""
    assert actual_output["total_requests"] == expected_output["total_requests"], (
        f"Expected {expected_output['total_requests']} requests, "
        f"got {actual_output['total_requests']}"
    )


def test_current_time_propagation(actual_output, expected_output):
    """Verify the simulation timestamp was correctly propagated to output."""
    assert actual_output["current_time"] == expected_output["current_time"], (
        "Current time not correctly propagated"
    )


def test_result_count_matches(actual_output, expected_output):
    """Verify the number of result entries matches expected count."""
    assert len(actual_output["results"]) == len(expected_output["results"]), (
        f"Result count mismatch: got {len(actual_output['results'])}, "
        f"expected {len(expected_output['results'])}"
    )


def test_order_service_routing_checkout(actual_output, expected_output):
    """Verify checkout-flow request to order-service routes to correct backend.

    Tests that consistent hashing with source+destination key selects the
    appropriate backend when the primary has an open circuit breaker.
    """
    actual = next(r for r in actual_output["results"]
                  if r["request_id"] == "req-101")
    expected = next(r for r in expected_output["results"]
                    if r["request_id"] == "req-101")
    assert actual["status"] == expected["status"], (
        f"req-101 status: got {actual['status']}, expected {expected['status']}"
    )
    assert actual["routed_to"] == expected["routed_to"], (
        f"req-101 routed_to: got {actual['routed_to']}, "
        f"expected {expected['routed_to']}"
    )
    assert actual["remaining_retries"] == expected["remaining_retries"], (
        f"req-101 remaining_retries: got {actual['remaining_retries']}, "
        f"expected {expected['remaining_retries']}"
    )


def test_payment_service_hash_key_routing(actual_output, expected_output):
    """Verify payment-service backend selection uses source+destination hash.

    With 3 backends, source-only hashing produces a different ring position
    than source+destination hashing, resulting in different backend selection.
    """
    actual = next(r for r in actual_output["results"]
                  if r["request_id"] == "req-102")
    expected = next(r for r in expected_output["results"]
                    if r["request_id"] == "req-102")
    assert actual["routed_to"] == expected["routed_to"], (
        f"req-102 routed_to: got {actual['routed_to']}, "
        f"expected {expected['routed_to']}. "
        "Hash key should include both source and destination."
    )
    assert actual["status"] == expected["status"], (
        f"req-102 status mismatch"
    )


def test_inventory_service_health_check(actual_output, expected_output):
    """Verify inventory backends are considered healthy based on heartbeat TTL.

    Backends have old registration timestamps but recent heartbeats.
    Health check must use last_heartbeat_timestamp, not registration_timestamp.
    """
    actual = next(r for r in actual_output["results"]
                  if r["request_id"] == "req-103")
    expected = next(r for r in expected_output["results"]
                    if r["request_id"] == "req-103")
    assert actual["status"] == expected["status"], (
        f"req-103 status: got {actual['status']}, expected {expected['status']}. "
        "Backends should be healthy (heartbeat is recent)."
    )
    assert actual["routed_to"] == expected["routed_to"], (
        f"req-103 routed_to: got {actual['routed_to']}, "
        f"expected {expected['routed_to']}"
    )


def test_notification_service_health_and_circuit(actual_output, expected_output):
    """Verify notification-service handles both health and circuit breaker correctly.

    Backends have old registrations but fresh heartbeats (health check test).
    One backend has an open circuit (circuit breaker ordering test).
    """
    actual = next(r for r in actual_output["results"]
                  if r["request_id"] == "req-104")
    expected = next(r for r in expected_output["results"]
                    if r["request_id"] == "req-104")
    assert actual["status"] == expected["status"], (
        f"req-104 status: got {actual['status']}, expected {expected['status']}"
    )
    assert actual["routed_to"] == expected["routed_to"], (
        f"req-104 routed_to: got {actual['routed_to']}, "
        f"expected {expected['routed_to']}"
    )
    assert actual["remaining_retries"] == expected["remaining_retries"], (
        f"req-104 remaining_retries: got {actual['remaining_retries']}, "
        f"expected {expected['remaining_retries']}. "
        "Circuit breaker should be checked before consuming retry budget."
    )


def test_order_service_circuit_breaker_ordering(actual_output, expected_output):
    """Verify circuit breaker is evaluated before retry budget consumption.

    When batch-processor routes to order-service, the primary backend has
    an open circuit. The pipeline should skip it without consuming retries.
    """
    actual = next(r for r in actual_output["results"]
                  if r["request_id"] == "req-105")
    expected = next(r for r in expected_output["results"]
                    if r["request_id"] == "req-105")
    assert actual["remaining_retries"] == expected["remaining_retries"], (
        f"req-105 remaining_retries: got {actual['remaining_retries']}, "
        f"expected {expected['remaining_retries']}. "
        "Circuit breaker check must not consume retry budget."
    )
    assert actual["routed_to"] == expected["routed_to"], (
        f"req-105 routed_to: got {actual['routed_to']}, "
        f"expected {expected['routed_to']}"
    )
    assert actual["attempts"] == expected["attempts"], (
        f"req-105 attempts: got {actual['attempts']}, "
        f"expected {expected['attempts']}"
    )


def test_payment_refund_circuit_and_hash(actual_output, expected_output):
    """Verify payment refund request handles circuit breaker with correct hash.

    The admin-panel to payment-service route should use the combined hash key
    and properly handle the open circuit on payment-backend-1.
    """
    actual = next(r for r in actual_output["results"]
                  if r["request_id"] == "req-106")
    expected = next(r for r in expected_output["results"]
                    if r["request_id"] == "req-106")
    assert actual["status"] == expected["status"], (
        f"req-106 status: got {actual['status']}, expected {expected['status']}"
    )
    assert actual["routed_to"] == expected["routed_to"], (
        f"req-106 routed_to: got {actual['routed_to']}, "
        f"expected {expected['routed_to']}"
    )
    assert actual["remaining_retries"] == expected["remaining_retries"], (
        f"req-106 remaining_retries: got {actual['remaining_retries']}, "
        f"expected {expected['remaining_retries']}"
    )


def test_all_results_match_exactly(actual_output, expected_output):
    """Verify complete output matches expected output exactly.

    This is the comprehensive check that validates all routing decisions,
    retry budgets, and backend selections match the expected correct output.
    """
    assert actual_output == expected_output, (
        "Full output mismatch. Pipeline has routing errors."
    )
