"""Tests for task runner pipeline output verification.

Validates that the pipeline produces correct results when executing
a multi-stage integration pipeline with parallel builds, retry logic,
and dependency-ordered execution.
"""

import json
import os
import pytest
from pathlib import Path


EXPECTED_PATH = Path("/tests/expected_output.json")
OUTPUT_PATH = "/app/output_eval.json"
TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_output(path):
    """Load an output file with symlink and escape protection."""
    assert os.path.exists(path), f"Output not found: {path}"
    assert not os.path.islink(path), f"Output must not be a symlink: {path}"
    real_path = os.path.realpath(path)
    assert real_path.startswith("/app/"), f"Output escapes /app: {real_path}"
    with open(path, "r") as f:
        return json.load(f)


def _load_expected(filename):
    """Load expected output from sealed test fixtures."""
    with open(os.path.join(TESTS_DIR, filename), "r") as f:
        return json.load(f)


@pytest.fixture
def output():
    """Load the pipeline output for verification."""
    return _load_output(OUTPUT_PATH)


@pytest.fixture
def expected():
    """Load the expected output for comparison."""
    return _load_expected("expected_output.json")


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
    """Verify tasks executed in the correct dependency-respecting order.

    Within each dependency level, parallel tasks are ordered alphabetically
    by task name for deterministic scheduling.
    """
    assert output["tasks_executed"] == expected["tasks_executed"], (
        f"Execution order: {output['tasks_executed']}, "
        f"expected: {expected['tasks_executed']}"
    )


def test_build_tasks_priority_order(output):
    """Verify parallel build tasks are ordered alphabetically for deterministic output.

    The resolver orders tasks within the same dependency level alphabetically
    by task name: build-api, build-gateway, build-worker.
    """
    executed = output["tasks_executed"]
    build_tasks = [t for t in executed if t.startswith("build-")]
    assert build_tasks == ["build-api", "build-gateway", "build-worker"], (
        f"Build task order: {build_tasks}, "
        f"expected: ['build-api', 'build-gateway', 'build-worker'] (alphabetical order)"
    )


def test_setup_env_success(output):
    """Verify the setup-env task with retries completed successfully."""
    assert "setup-env" in output["results"], "setup-env task not in results"
    result = output["results"]["setup-env"]
    assert result["status"] == "success", (
        f"setup-env status: {result['status']}, expected 'success'"
    )


def test_setup_env_variable_resolved(output):
    """Verify that ARTIFACT_TAG variable is resolved to its actual value in build_vars.sh.

    Bug 1 (variable expansion): If unresolved, the command would contain a literal
    '$ARTIFACT_TAG' instead of the expanded value 'release-3.2.1'.
    The build_vars.sh command must contain 'tag=release-3.2.1'.
    """
    result = output["results"]["setup-env"]
    commands = result.get("commands", [])
    # Find the command that writes build_vars.sh
    build_vars_cmds = [c for c in commands if "build_vars.sh" in c.get("command", "")]
    assert len(build_vars_cmds) > 0, "No build_vars.sh command found in setup-env"

    build_vars_cmd = build_vars_cmds[0]["command"]
    # Must contain the resolved value, not a variable reference
    assert "release-3.2.1" in build_vars_cmd, (
        f"Variable not resolved in build_vars.sh command: '{build_vars_cmd}'. "
        f"Expected 'release-3.2.1' but got unresolved variable reference."
    )
    assert "artifact=3.2.1" in build_vars_cmd, (
        f"VERSION variable not expanded in build_vars.sh command: '{build_vars_cmd}'. "
        f"Expected 'artifact=3.2.1' from two-pass expansion of DEPLOY_TEMPLATE."
    )
    assert "$ARTIFACT_TAG" not in build_vars_cmd, (
        f"Unresolved variable '$ARTIFACT_TAG' found in command: '{build_vars_cmd}'. "
        f"Variable expansion bug not fixed."
    )


def test_setup_env_retry_occurred(output):
    """Verify that a retry genuinely occurred during setup-env execution.

    Bug 3 (retry state): The .attempt file test command must appear at least twice —
    first attempt fails (exit_code=1), retry succeeds (exit_code=0). This proves
    the retry mechanism was exercised and workspace state was preserved.
    """
    result = output["results"]["setup-env"]
    commands = result.get("commands", [])

    # Find all commands that test for .attempt file (the retry trigger)
    attempt_cmds = [
        c for c in commands
        if ".attempt" in c.get("command", "") and "test -f" in c.get("command", "")
    ]
    assert len(attempt_cmds) >= 2, (
        f"Expected at least 2 retry-trigger commands (.attempt test), "
        f"found {len(attempt_cmds)}. Retry did not occur."
    )

    # First attempt must fail (exit_code=1), proving retry is needed
    assert attempt_cmds[0]["exit_code"] == 1, (
        f"First .attempt command should fail (exit_code=1), "
        f"got exit_code={attempt_cmds[0]['exit_code']}"
    )

    # Second attempt must succeed (exit_code=0), proving retry worked
    assert attempt_cmds[1]["exit_code"] == 0, (
        f"Second .attempt command should succeed (exit_code=0), "
        f"got exit_code={attempt_cmds[1]['exit_code']}"
    )


def test_setup_env_variable_persists_after_retry(output):
    """Verify that exported environment variables persist across retry boundaries.

    After the retry succeeds, the ARTIFACT_TAG export must still be in effect,
    evidenced by the resolved value appearing in commands after the retry.
    """
    result = output["results"]["setup-env"]
    commands = result.get("commands", [])

    # Find the index of the successful retry (second .attempt test)
    retry_success_idx = None
    attempt_count = 0
    for i, c in enumerate(commands):
        if ".attempt" in c.get("command", "") and "test -f" in c.get("command", ""):
            attempt_count += 1
            if attempt_count == 2:
                retry_success_idx = i
                break

    assert retry_success_idx is not None, "Could not find retry success point"

    # Commands after retry must use the resolved ARTIFACT_TAG value
    post_retry_commands = commands[retry_success_idx + 1:]
    assert len(post_retry_commands) > 0, "No commands found after retry"

    # The build_vars.sh write must occur after retry with resolved value
    post_retry_text = " ".join(c.get("command", "") for c in post_retry_commands)
    assert "release-3.2.1" in post_retry_text, (
        f"ARTIFACT_TAG value 'release-3.2.1' not found in post-retry commands. "
        f"Environment variable did not persist across retry boundary."
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


def test_output_derived_from_eval_taskfile():
    """Verify output was computed from running the fixed pipeline on eval_taskfile.json.

    This test reads the eval taskfile directly and cross-checks that the output
    contains values that can only be produced by running the fixed pipeline on
    this specific input. An agent that hardcodes the output file without running
    the pipeline cannot pass this test without also correctly deriving these values.

    Specifically: setup-env's DEPLOY_TEMPLATE uses VERSION and ARTIFACT_TAG env vars.
    The fixed pipeline must two-pass expand these to produce artifact=3.2.1 and
    tag=release-3.2.1 in the build_vars.sh command.
    """
    with open("/app/eval_taskfile.json", "r") as f:
        taskfile = json.load(f)

    # Verify we're testing the right taskfile
    setup_env = taskfile.get("tasks", {}).get("setup-env", {})
    env = setup_env.get("env", {})
    version = env.get("VERSION")
    template = env.get("DEPLOY_TEMPLATE")

    assert version is not None, "eval_taskfile.json must have setup-env.env.VERSION"
    assert template is not None, "eval_taskfile.json must have setup-env.env.DEPLOY_TEMPLATE"

    # Derive expected values from the taskfile
    # VERSION=3.2.1 → ARTIFACT_TAG=release-3.2.1 (set by export in setup-env commands)
    # DEPLOY_TEMPLATE='artifact=$VERSION tag=$ARTIFACT_TAG' → two-pass expansion
    expected_version_in_output = version  # e.g., "3.2.1"
    expected_tag = f"release-{version}"  # e.g., "release-3.2.1"

    # Load actual output and verify it contains values derived from this taskfile
    output = _load_output(OUTPUT_PATH)
    result = output["results"]["setup-env"]
    commands = result.get("commands", [])
    build_vars_cmds = [c for c in commands if "build_vars.sh" in c.get("command", "")]

    assert len(build_vars_cmds) > 0, "setup-env must produce a build_vars.sh command"
    cmd = build_vars_cmds[0]["command"]

    assert f"artifact={expected_version_in_output}" in cmd, (
        f"build_vars.sh command must contain 'artifact={expected_version_in_output}' "
        f"(derived from VERSION={version} in eval_taskfile.json), got: {cmd}"
    )
    assert f"tag={expected_tag}" in cmd, (
        f"build_vars.sh command must contain 'tag={expected_tag}' "
        f"(derived from ARTIFACT_TAG=release-{version}), got: {cmd}"
    )
