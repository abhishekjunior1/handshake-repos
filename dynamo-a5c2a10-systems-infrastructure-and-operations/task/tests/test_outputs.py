"""
Tests for the distributed task queue pipeline.

Validates that the pipeline produces correct output on hidden test data
with multiple consumers, rate limiting, retries, and failures.
"""

import json
import os
import pytest


TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_json(path):
    """Load a JSON file and return parsed data."""
    with open(path, "r") as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found: {OUTPUT_PATH}"
    return load_json(OUTPUT_PATH)


@pytest.fixture
def expected_output():
    """Load the expected pipeline output."""
    assert os.path.exists(EXPECTED_PATH), f"Expected output not found: {EXPECTED_PATH}"
    return load_json(EXPECTED_PATH)


class TestPipelineSummary:
    """Tests for the processing summary totals."""

    def test_total_tasks_count(self, actual_output, expected_output):
        """Verify the total number of tasks processed matches expected."""
        assert actual_output["summary"]["total_tasks"] == expected_output["summary"]["total_tasks"]

    def test_completed_count(self, actual_output, expected_output):
        """Verify the number of successfully completed tasks."""
        assert actual_output["summary"]["completed"] == expected_output["summary"]["completed"]

    def test_failed_count(self, actual_output, expected_output):
        """Verify the number of failed (dead-lettered) tasks."""
        assert actual_output["summary"]["failed"] == expected_output["summary"]["failed"]

    def test_dlq_count(self, actual_output, expected_output):
        """Verify the dead letter queue count in summary."""
        assert actual_output["summary"]["dead_lettered"] == expected_output["summary"]["dead_lettered"]

    def test_total_ticks(self, actual_output, expected_output):
        """Verify processing completed in expected number of ticks."""
        assert actual_output["summary"]["total_ticks"] == expected_output["summary"]["total_ticks"]


class TestTaskOutcomes:
    """Tests for individual task processing outcomes."""

    def test_all_task_ids_present(self, actual_output, expected_output):
        """Verify all expected tasks have outcomes recorded."""
        expected_ids = set(expected_output["task_outcomes"].keys())
        actual_ids = set(actual_output["task_outcomes"].keys())
        assert actual_ids == expected_ids

    def test_task_statuses_match(self, actual_output, expected_output):
        """Verify each task's final status matches expected."""
        for task_id, expected in expected_output["task_outcomes"].items():
            actual = actual_output["task_outcomes"].get(task_id, {})
            assert actual.get("status") == expected["status"], \
                f"Task {task_id}: expected status '{expected['status']}', got '{actual.get('status')}'"

    def test_retry_counts_match(self, actual_output, expected_output):
        """Verify retry counts for each task match expected values."""
        for task_id, expected in expected_output["task_outcomes"].items():
            actual = actual_output["task_outcomes"].get(task_id, {})
            assert actual.get("retries_used") == expected["retries_used"], \
                f"Task {task_id}: expected {expected['retries_used']} retries, got {actual.get('retries_used')}"

    def test_consumer_assignments_match(self, actual_output, expected_output):
        """Verify tasks were assigned to correct consumers."""
        for task_id, expected in expected_output["task_outcomes"].items():
            actual = actual_output["task_outcomes"].get(task_id, {})
            assert actual.get("final_consumer") == expected["final_consumer"], \
                f"Task {task_id}: expected consumer '{expected['final_consumer']}', got '{actual.get('final_consumer')}'"

    def test_completed_at_tick_match(self, actual_output, expected_output):
        """Verify tasks completed or dead-lettered at the expected tick."""
        for task_id, expected in expected_output["task_outcomes"].items():
            actual = actual_output["task_outcomes"].get(task_id, {})
            assert actual.get("completed_at_tick") == expected["completed_at_tick"], \
                f"Task {task_id}: expected completed_at_tick {expected['completed_at_tick']}, got {actual.get('completed_at_tick')}"


class TestDeadLetterQueue:
    """Tests for dead letter queue routing."""

    def test_dlq_size(self, actual_output, expected_output):
        """Verify correct number of tasks in DLQ."""
        assert len(actual_output["dlq_contents"]) == len(expected_output["dlq_contents"])

    def test_dlq_task_ids(self, actual_output, expected_output):
        """Verify correct tasks were routed to DLQ."""
        expected_ids = {e["task_id"] for e in expected_output["dlq_contents"]}
        actual_ids = {e["task_id"] for e in actual_output["dlq_contents"]}
        assert actual_ids == expected_ids

    def test_dlq_retry_counts(self, actual_output, expected_output):
        """Verify DLQ entries have correct final retry counts."""
        expected_map = {e["task_id"]: e for e in expected_output["dlq_contents"]}
        actual_map = {e["task_id"]: e for e in actual_output["dlq_contents"]}
        for task_id, expected in expected_map.items():
            actual = actual_map.get(task_id, {})
            assert actual.get("final_retry_count") == expected["final_retry_count"], \
                f"DLQ {task_id}: expected retry count {expected['final_retry_count']}, got {actual.get('final_retry_count')}"

    def test_dlq_failure_reasons(self, actual_output, expected_output):
        """Verify DLQ entries have correct failure reasons."""
        expected_map = {e["task_id"]: e for e in expected_output["dlq_contents"]}
        actual_map = {e["task_id"]: e for e in actual_output["dlq_contents"]}
        for task_id, expected in expected_map.items():
            actual = actual_map.get(task_id, {})
            assert actual.get("failure_reason") == expected["failure_reason"], \
                f"DLQ {task_id}: expected reason '{expected['failure_reason']}', got '{actual.get('failure_reason')}'"

    def test_dlq_routed_at_tick(self, actual_output, expected_output):
        """Verify DLQ entries have correct routing tick."""
        expected_map = {e["task_id"]: e for e in expected_output["dlq_contents"]}
        actual_map = {e["task_id"]: e for e in actual_output["dlq_contents"]}
        for task_id, expected in expected_map.items():
            actual = actual_map.get(task_id, {})
            assert actual.get("routed_at_tick") == expected["routed_at_tick"], \
                f"DLQ {task_id}: expected routed_at_tick {expected['routed_at_tick']}, got {actual.get('routed_at_tick')}"

    def test_dlq_original_priority(self, actual_output, expected_output):
        """Verify DLQ entries have correct original priority."""
        expected_map = {e["task_id"]: e for e in expected_output["dlq_contents"]}
        actual_map = {e["task_id"]: e for e in actual_output["dlq_contents"]}
        for task_id, expected in expected_map.items():
            actual = actual_map.get(task_id, {})
            assert actual.get("original_priority") == expected["original_priority"], \
                f"DLQ {task_id}: expected priority {expected['original_priority']}, got {actual.get('original_priority')}"


class TestConsumerStats:
    """Tests for per-consumer statistics."""

    def test_consumer_ids_present(self, actual_output, expected_output):
        """Verify all consumers have stats recorded."""
        expected_ids = set(expected_output["consumer_stats"].keys())
        actual_ids = set(actual_output["consumer_stats"].keys())
        assert actual_ids == expected_ids

    def test_tasks_assigned_per_consumer(self, actual_output, expected_output):
        """Verify task assignment counts per consumer."""
        for cid, expected in expected_output["consumer_stats"].items():
            actual = actual_output["consumer_stats"].get(cid, {})
            assert actual.get("tasks_assigned") == expected["tasks_assigned"], \
                f"Consumer {cid}: expected {expected['tasks_assigned']} assigned, got {actual.get('tasks_assigned')}"

    def test_tasks_completed_per_consumer(self, actual_output, expected_output):
        """Verify completion counts per consumer."""
        for cid, expected in expected_output["consumer_stats"].items():
            actual = actual_output["consumer_stats"].get(cid, {})
            assert actual.get("tasks_completed") == expected["tasks_completed"], \
                f"Consumer {cid}: expected {expected['tasks_completed']} completed, got {actual.get('tasks_completed')}"

    def test_tasks_failed_per_consumer(self, actual_output, expected_output):
        """Verify failure counts per consumer."""
        for cid, expected in expected_output["consumer_stats"].items():
            actual = actual_output["consumer_stats"].get(cid, {})
            assert actual.get("tasks_failed") == expected["tasks_failed"], \
                f"Consumer {cid}: expected {expected['tasks_failed']} failed, got {actual.get('tasks_failed')}"


class TestProcessingLog:
    """Tests for the chronological processing log."""

    def test_log_not_empty(self, actual_output):
        """Verify processing log contains events."""
        assert len(actual_output["processing_log"]) > 0

    def test_log_events_match(self, actual_output, expected_output):
        """Verify processing log matches expected event sequence."""
        assert len(actual_output["processing_log"]) == len(expected_output["processing_log"]), \
            f"Expected {len(expected_output['processing_log'])} events, got {len(actual_output['processing_log'])}"

    def test_log_chronological_order(self, actual_output):
        """Verify events are in non-decreasing tick order."""
        ticks = [e["tick"] for e in actual_output["processing_log"]]
        assert ticks == sorted(ticks), "Processing log is not in chronological order"

    def test_dispatch_events_count(self, actual_output, expected_output):
        """Verify correct number of dispatch events."""
        actual_dispatches = [e for e in actual_output["processing_log"] if e["event"] == "dispatched"]
        expected_dispatches = [e for e in expected_output["processing_log"] if e["event"] == "dispatched"]
        assert len(actual_dispatches) == len(expected_dispatches)
