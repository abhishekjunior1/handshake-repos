"""Tests for task runner pipeline output verification.

Validates that the pipeline produces correct results when executing
a multi-stage integration pipeline with parallel builds, retry logic,
and dependency-ordered execution.
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


def test_pipeline_success(output):
    """Verify the pipeline completes successfully."""
    assert output["success"] is True, (
        f"Pipeline failed: success={output.get('success')}"
    )


def test_all_tasks_executed(output, expected):
    """Verify all expected tasks were executed."""
    assert set(output["tasks_executed"]) == set(expected["tasks_executed"]), (
        f"Tasks executed: {output['tasks_executed']}, "
        f"expected: {expected['tasks_executed']}"
    )


def test_task_execution_order(output, expected):
    """Verify tasks executed in the correct dependency-respecting order."""
    assert output["tasks_executed"] == expected["tasks_executed"], (
        f"Execution order: {output['tasks_executed']}, "
        f"expected: {expected['tasks_executed']}"
    )


def test_setup_env_success(output):
    """Verify the setup-env task with retries completed successfully."""
    assert "setup-env" in output["results"], "setup-env task not in results"
    result = output["results"]["setup-env"]
    assert result["status"] == "success", (
        f"setup-env status: {result['status']}, expected 'success'"
    )


def test_setup_env_variable_capture(output):
    """Verify that environment variables captured during setup persist across retries."""
    result = output["results"]["setup-env"]
    commands = result.get("commands", [])
    # Find the command that uses ARTIFACT_TAG (the echo with tag=...)
    tag_commands = [c for c in commands if "tag=" in c.get("command", "")]
    assert len(tag_commands) > 0, "No tag command found in setup-env results"
    # The tag command should produce output with the captured value
    tag_cmd = tag_commands[0]
    assert tag_cmd["exit_code"] == 0, (
        f"Tag command failed with exit_code={tag_cmd['exit_code']}"
    )


def test_build_tasks_all_succeed(output):
    """Verify all build tasks completed successfully."""
    build_tasks = ["build-api", "build-worker", "build-gateway"]
    for task_name in build_tasks:
        assert task_name in output["results"], f"{task_name} not in results"
        assert output["results"][task_name]["status"] == "success", (
            f"{task_name} status: {output['results'][task_name]['status']}"
        )


def test_package_task_success(output):
    """Verify the final packaging task completed successfully."""
    assert "package" in output["results"], "package task not in results"
    result = output["results"]["package"]
    assert result["status"] == "success", (
        f"package status: {result['status']}, expected 'success'"
    )


def test_task_count(output, expected):
    """Verify the correct number of tasks were executed."""
    assert len(output["tasks_executed"]) == len(expected["tasks_executed"]), (
        f"Executed {len(output['tasks_executed'])} tasks, "
        f"expected {len(expected['tasks_executed'])}"
    )


def test_no_failed_tasks(output):
    """Verify no tasks have failed status in results."""
    for task_name, result in output["results"].items():
        assert result["status"] == "success", (
            f"Task '{task_name}' has status '{result['status']}'"
        )
