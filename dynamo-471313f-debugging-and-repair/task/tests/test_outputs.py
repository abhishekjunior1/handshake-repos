"""Tests for the work-stealing scheduler simulator output correctness."""

import json
import os

import pytest


def load_output():
    """Load the pipeline output."""
    output_path = "/app/output.json"
    if not os.path.exists(output_path):
        pytest.fail("output.json not found — pipeline did not produce output")
    with open(output_path) as f:
        return json.load(f)


def load_expected():
    """Load the expected output."""
    expected_path = "/tests/expected_output.json"
    if not os.path.exists(expected_path):
        pytest.fail("expected_output.json not found")
    with open(expected_path) as f:
        return json.load(f)


class TestSchedulingMetrics:
    """Tests for overall scheduling metrics correctness."""

    def test_makespan(self):
        """Verify the simulation produces the correct makespan (total time to complete all tasks)."""
        output = load_output()
        expected = load_expected()
        assert output["scheduling_metrics"]["makespan"] == expected["scheduling_metrics"]["makespan"], \
            f"Makespan mismatch: got {output['scheduling_metrics']['makespan']}, expected {expected['scheduling_metrics']['makespan']}"

    def test_total_tasks(self):
        """Verify all tasks in the DAG were executed."""
        output = load_output()
        expected = load_expected()
        assert output["scheduling_metrics"]["total_tasks"] == expected["scheduling_metrics"]["total_tasks"]

    def test_speedup(self):
        """Verify the parallel speedup metric matches expected value."""
        output = load_output()
        expected = load_expected()
        assert abs(output["scheduling_metrics"]["speedup"] - expected["scheduling_metrics"]["speedup"]) < 1e-4, \
            f"Speedup mismatch: got {output['scheduling_metrics']['speedup']}, expected {expected['scheduling_metrics']['speedup']}"

    def test_critical_path_length(self):
        """Verify the critical path length computation is correct."""
        output = load_output()
        expected = load_expected()
        assert abs(output["scheduling_metrics"]["critical_path_length"] - expected["scheduling_metrics"]["critical_path_length"]) < 1e-4


class TestCompletionOrder:
    """Tests for task completion ordering correctness."""

    def test_completion_order(self):
        """Verify tasks complete in the correct order determined by scheduling priority and dependency resolution."""
        output = load_output()
        expected = load_expected()
        assert output["completion_order"] == expected["completion_order"], \
            f"Completion order mismatch:\n  got:      {output['completion_order']}\n  expected: {expected['completion_order']}"

    def test_all_tasks_completed(self):
        """Verify every task in the DAG appears in the completion order."""
        output = load_output()
        expected = load_expected()
        assert set(output["completion_order"]) == set(expected["completion_order"])


class TestExecutionTrace:
    """Tests for per-task execution trace correctness."""

    def test_execution_trace_count(self):
        """Verify the execution trace contains an entry for every task."""
        output = load_output()
        expected = load_expected()
        assert len(output["execution_trace"]) == len(expected["execution_trace"])

    def test_task_start_times(self):
        """Verify each task starts at the correct simulation tick based on dependency resolution and scheduling."""
        output = load_output()
        expected = load_expected()
        output_starts = {e["task_id"]: e["start_time"] for e in output["execution_trace"]}
        expected_starts = {e["task_id"]: e["start_time"] for e in expected["execution_trace"]}
        for task_id in expected_starts:
            assert task_id in output_starts, f"Task {task_id} missing from output trace"
            assert output_starts[task_id] == expected_starts[task_id], \
                f"Task {task_id} start_time mismatch: got {output_starts[task_id]}, expected {expected_starts[task_id]}"

    def test_task_finish_times(self):
        """Verify each task finishes at the correct simulation tick."""
        output = load_output()
        expected = load_expected()
        output_finishes = {e["task_id"]: e["finish_time"] for e in output["execution_trace"]}
        expected_finishes = {e["task_id"]: e["finish_time"] for e in expected["execution_trace"]}
        for task_id in expected_finishes:
            assert task_id in output_finishes, f"Task {task_id} missing from output trace"
            assert output_finishes[task_id] == expected_finishes[task_id], \
                f"Task {task_id} finish_time mismatch: got {output_finishes[task_id]}, expected {expected_finishes[task_id]}"

    def test_worker_assignments(self):
        """Verify tasks are assigned to the correct workers based on scheduling and work-stealing."""
        output = load_output()
        expected = load_expected()
        output_workers = {e["task_id"]: e["worker_id"] for e in output["execution_trace"]}
        expected_workers = {e["task_id"]: e["worker_id"] for e in expected["execution_trace"]}
        for task_id in expected_workers:
            assert task_id in output_workers, f"Task {task_id} missing from output trace"
            assert output_workers[task_id] == expected_workers[task_id], \
                f"Task {task_id} worker mismatch: got {output_workers[task_id]}, expected {expected_workers[task_id]}"

    def test_stolen_flags(self):
        """Verify the stolen flag correctly identifies tasks obtained via work-stealing."""
        output = load_output()
        expected = load_expected()
        output_stolen = {e["task_id"]: e["stolen"] for e in output["execution_trace"]}
        expected_stolen = {e["task_id"]: e["stolen"] for e in expected["execution_trace"]}
        for task_id in expected_stolen:
            assert task_id in output_stolen, f"Task {task_id} missing from output trace"
            assert output_stolen[task_id] == expected_stolen[task_id], \
                f"Task {task_id} stolen flag mismatch: got {output_stolen[task_id]}, expected {expected_stolen[task_id]}"


class TestStealStatistics:
    """Tests for work-stealing protocol statistics."""

    def test_steal_successes(self):
        """Verify the number of successful steals matches expected work distribution."""
        output = load_output()
        expected = load_expected()
        assert output["steal_statistics"]["total_successes"] == expected["steal_statistics"]["total_successes"], \
            f"Steal successes mismatch: got {output['steal_statistics']['total_successes']}, expected {expected['steal_statistics']['total_successes']}"

    def test_steal_attempts(self):
        """Verify total steal attempts are consistent with the simulation."""
        output = load_output()
        expected = load_expected()
        assert output["steal_statistics"]["total_attempts"] == expected["steal_statistics"]["total_attempts"]


class TestDependencyTimeline:
    """Tests for dependency resolution timeline correctness."""

    def test_dependency_events(self):
        """Verify dependency resolution events occur at correct simulation ticks."""
        output = load_output()
        expected = load_expected()
        assert output["dependency_timeline"] == expected["dependency_timeline"], \
            "Dependency timeline mismatch"


class TestWorkerStatistics:
    """Tests for per-worker execution statistics correctness."""

    def test_worker_utilization(self):
        """Verify per-worker utilization metrics match expected values based on task assignments."""
        output = load_output()
        expected = load_expected()
        for out_w, exp_w in zip(output["worker_statistics"]["per_worker"],
                                expected["worker_statistics"]["per_worker"]):
            assert out_w["worker_id"] == exp_w["worker_id"]
            assert out_w["tasks_executed"] == exp_w["tasks_executed"], \
                f"Worker {out_w['worker_id']} tasks_executed mismatch: got {out_w['tasks_executed']}, expected {exp_w['tasks_executed']}"
            assert out_w["idle_ticks"] == exp_w["idle_ticks"], \
                f"Worker {out_w['worker_id']} idle_ticks mismatch: got {out_w['idle_ticks']}, expected {exp_w['idle_ticks']}"
            assert out_w["execution_ticks"] == exp_w["execution_ticks"], \
                f"Worker {out_w['worker_id']} execution_ticks mismatch"

    def test_total_simulation_ticks(self):
        """Verify the total simulation tick count is correct."""
        output = load_output()
        expected = load_expected()
        assert output["scheduling_metrics"]["total_simulation_ticks"] == \
            expected["scheduling_metrics"]["total_simulation_ticks"], \
            f"total_simulation_ticks mismatch: got {output['scheduling_metrics']['total_simulation_ticks']}, expected {expected['scheduling_metrics']['total_simulation_ticks']}"

    def test_efficiency(self):
        """Verify the parallel efficiency metric matches expected value."""
        output = load_output()
        expected = load_expected()
        assert abs(output["scheduling_metrics"]["efficiency"] - expected["scheduling_metrics"]["efficiency"]) < 1e-4, \
            f"Efficiency mismatch: got {output['scheduling_metrics']['efficiency']}, expected {expected['scheduling_metrics']['efficiency']}"
