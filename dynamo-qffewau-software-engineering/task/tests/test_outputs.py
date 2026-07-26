"""
Verification tests for the task execution pipeline output.
Checks that the agent produced correct output for both eval taskfiles.
The agent was instructed to run the pipeline on all eval taskfiles before submission.
"""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _load_output(path):
    """Load an output file with symlink protection."""
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


# ── Eval 1 tests ─────────────────────────────────────────────────────────────

def test_eval1_output_exists():
    """The agent must produce /app/output_eval_1.json."""
    assert os.path.exists("/app/output_eval_1.json"), "output_eval_1.json not found"


def test_eval2_output_exists():
    """The agent must produce /app/output_eval_2.json."""
    assert os.path.exists("/app/output_eval_2.json"), "output_eval_2.json not found"


class TestEval1PipelineSuccess:
    """Tests for top-level pipeline success on eval taskfile 1."""

    def test_pipeline_success(self):
        """Verify the pipeline completes successfully."""
        output = _load_output("/app/output_eval_1.json")
        assert output["success"] is True, (
            f"Pipeline failed: success={output.get('success')}"
        )

    def test_all_tasks_executed(self):
        """Verify all expected tasks were executed."""
        output = _load_output("/app/output_eval_1.json")
        expected = _load_expected("expected_output.json")
        assert set(output["tasks_executed"]) == set(expected["tasks_executed"]), (
            f"Tasks executed: {output['tasks_executed']}, expected: {expected['tasks_executed']}"
        )

    def test_task_execution_order(self):
        """Verify tasks executed in the correct dependency-respecting order.

        Within each dependency level, parallel tasks are ordered alphabetically
        by task name for deterministic scheduling.
        """
        output = _load_output("/app/output_eval_1.json")
        expected = _load_expected("expected_output.json")
        assert output["tasks_executed"] == expected["tasks_executed"], (
            f"Execution order: {output['tasks_executed']}, expected: {expected['tasks_executed']}"
        )

    def test_task_count(self):
        """Verify the correct number of tasks were executed."""
        output = _load_output("/app/output_eval_1.json")
        expected = _load_expected("expected_output.json")
        assert len(output["tasks_executed"]) == len(expected["tasks_executed"]), (
            f"Executed {len(output['tasks_executed'])} tasks, "
            f"expected {len(expected['tasks_executed'])}"
        )

    def test_no_failed_tasks(self):
        """Verify no tasks have failed status in results."""
        output = _load_output("/app/output_eval_1.json")
        for task_name, result in output["results"].items():
            assert result["status"] == "success", (
                f"Task '{task_name}' has status '{result['status']}'"
            )


class TestEval1BuildOrder:
    """Tests for parallel build task ordering on eval taskfile 1."""

    def test_build_tasks_alphabetical_order(self):
        """Verify parallel build tasks are ordered alphabetically for deterministic output.

        Bug 2: runner uses get_scheduled_groups() (priority order) instead of
        get_parallelizable_groups() (alphabetical order). With parallelism=3 and
        different sleep durations, as_completed returns tasks by completion time,
        not alphabetical order — only get_parallelizable_groups() sorts them correctly.
        """
        output = _load_output("/app/output_eval_1.json")
        executed = output["tasks_executed"]
        build_tasks = [t for t in executed if t.startswith("build-")]
        assert build_tasks == ["build-api", "build-gateway", "build-worker"], (
            f"Build task order: {build_tasks}, "
            f"expected: ['build-api', 'build-gateway', 'build-worker'] (alphabetical)"
        )

    def test_build_tasks_all_succeed(self):
        """Verify all build tasks completed successfully."""
        output = _load_output("/app/output_eval_1.json")
        for task_name in ["build-api", "build-worker", "build-gateway"]:
            assert task_name in output["results"], f"{task_name} not in results"
            assert output["results"][task_name]["status"] == "success", (
                f"{task_name} status: {output['results'][task_name]['status']}"
            )

    def test_package_task_success(self):
        """Verify the final packaging task completed successfully."""
        output = _load_output("/app/output_eval_1.json")
        assert "package" in output["results"], "package task not in results"
        assert output["results"]["package"]["status"] == "success", (
            f"package status: {output['results']['package']['status']}"
        )


class TestEval1VariableExpansion:
    """Tests for variable expansion bug on eval taskfile 1."""

    def test_setup_env_variable_resolved(self):
        """Verify ARTIFACT_TAG is resolved to its actual value in build_vars.sh.

        Bug 1 (variable expansion): second-pass regex iterates over 'command'
        (the original template) instead of 'result' (the partially-expanded string).
        This means $ARTIFACT_TAG introduced by ${DEPLOY_TEMPLATE} expansion is never
        resolved. The build_vars.sh command must contain 'tag=release-3.2.1'.
        """
        output = _load_output("/app/output_eval_1.json")
        result = output["results"]["setup-env"]
        commands = result.get("commands", [])
        build_vars_cmds = [c for c in commands if "build_vars.sh" in c.get("command", "")]
        assert len(build_vars_cmds) > 0, "No build_vars.sh command found in setup-env"

        cmd = build_vars_cmds[0]["command"]
        assert "release-3.2.1" in cmd, (
            f"ARTIFACT_TAG not resolved in build_vars.sh: '{cmd}'. "
            f"Expected 'release-3.2.1' — variable expansion bug not fixed."
        )
        assert "artifact=3.2.1" in cmd, (
            f"VERSION not expanded in build_vars.sh: '{cmd}'. "
            f"Expected 'artifact=3.2.1' from two-pass expansion of DEPLOY_TEMPLATE."
        )
        assert "$ARTIFACT_TAG" not in cmd, (
            f"Unresolved '$ARTIFACT_TAG' in command: '{cmd}'."
        )


class TestEval1RetryState:
    """Tests for retry state management bug on eval taskfile 1."""

    def test_setup_env_retry_occurred(self):
        """Verify a retry genuinely occurred during setup-env.

        Bug 3 (retry state): env rebuilt on retry loses captured exports.
        The .attempt file test must appear at least twice — first fails
        (exit_code=1), second succeeds (exit_code=0).
        """
        output = _load_output("/app/output_eval_1.json")
        result = output["results"]["setup-env"]
        commands = result.get("commands", [])
        attempt_cmds = [
            c for c in commands
            if ".attempt" in c.get("command", "") and "test -f" in c.get("command", "")
        ]
        assert len(attempt_cmds) >= 2, (
            f"Expected at least 2 retry-trigger commands, found {len(attempt_cmds)}. "
            f"Retry did not occur."
        )
        assert attempt_cmds[0]["exit_code"] == 1, (
            f"First .attempt should fail (exit_code=1), got {attempt_cmds[0]['exit_code']}"
        )
        assert attempt_cmds[1]["exit_code"] == 0, (
            f"Second .attempt should succeed (exit_code=0), got {attempt_cmds[1]['exit_code']}"
        )

    def test_setup_env_variable_persists_after_retry(self):
        """Verify exported variables persist across retry boundaries.

        After the retry succeeds, ARTIFACT_TAG export must still be in effect.
        """
        output = _load_output("/app/output_eval_1.json")
        result = output["results"]["setup-env"]
        commands = result.get("commands", [])

        retry_success_idx = None
        attempt_count = 0
        for i, c in enumerate(commands):
            if ".attempt" in c.get("command", "") and "test -f" in c.get("command", ""):
                attempt_count += 1
                if attempt_count == 2:
                    retry_success_idx = i
                    break

        assert retry_success_idx is not None, "Could not find retry success point"
        post_retry = commands[retry_success_idx + 1:]
        assert len(post_retry) > 0, "No commands after retry"
        post_text = " ".join(c.get("command", "") for c in post_retry)
        assert "release-3.2.1" in post_text, (
            f"ARTIFACT_TAG value not found in post-retry commands. "
            f"Variable did not persist across retry boundary."
        )


# ── Eval 2 tests ─────────────────────────────────────────────────────────────

class TestEval2PipelineSuccess:
    """Tests for top-level pipeline success on eval taskfile 2."""

    def test_pipeline_success(self):
        """Verify the pipeline completes successfully on second eval taskfile."""
        output = _load_output("/app/output_eval_2.json")
        assert output["success"] is True, (
            f"Pipeline failed: success={output.get('success')}"
        )

    def test_all_tasks_executed(self):
        """Verify all expected tasks were executed on second eval taskfile."""
        output = _load_output("/app/output_eval_2.json")
        expected = _load_expected("expected_output_2.json")
        assert set(output["tasks_executed"]) == set(expected["tasks_executed"]), (
            f"Tasks executed: {output['tasks_executed']}, expected: {expected['tasks_executed']}"
        )

    def test_task_execution_order(self):
        """Verify tasks executed in correct order on second eval taskfile."""
        output = _load_output("/app/output_eval_2.json")
        expected = _load_expected("expected_output_2.json")
        assert output["tasks_executed"] == expected["tasks_executed"], (
            f"Execution order: {output['tasks_executed']}, expected: {expected['tasks_executed']}"
        )

    def test_no_failed_tasks(self):
        """Verify no tasks failed on second eval taskfile."""
        output = _load_output("/app/output_eval_2.json")
        for task_name, result in output["results"].items():
            assert result["status"] == "success", (
                f"Task '{task_name}' has status '{result['status']}'"
            )


class TestEval2DeployOrder:
    """Tests for parallel deploy task ordering on eval taskfile 2."""

    def test_deploy_tasks_alphabetical_order(self):
        """Verify parallel deploy tasks are ordered alphabetically.

        Bug 2: same ordering bug as eval 1 but with different service names
        (deploy-auth, deploy-backend, deploy-proxy) and different sleep durations,
        confirming hardcoding the first config's answer would fail here.
        """
        output = _load_output("/app/output_eval_2.json")
        executed = output["tasks_executed"]
        deploy_tasks = [t for t in executed if t.startswith("deploy-")]
        assert deploy_tasks == ["deploy-auth", "deploy-backend", "deploy-proxy"], (
            f"Deploy task order: {deploy_tasks}, "
            f"expected: ['deploy-auth', 'deploy-backend', 'deploy-proxy'] (alphabetical)"
        )

    def test_deploy_tasks_all_succeed(self):
        """Verify all deploy tasks completed successfully."""
        output = _load_output("/app/output_eval_2.json")
        for task_name in ["deploy-auth", "deploy-backend", "deploy-proxy"]:
            assert task_name in output["results"], f"{task_name} not in results"
            assert output["results"][task_name]["status"] == "success", (
                f"{task_name} status: {output['results'][task_name]['status']}"
            )

    def test_finalize_task_success(self):
        """Verify the finalize task completed successfully."""
        output = _load_output("/app/output_eval_2.json")
        assert "finalize" in output["results"], "finalize task not in results"
        assert output["results"]["finalize"]["status"] == "success"


class TestEval2VariableExpansion:
    """Tests for variable expansion bug on eval taskfile 2."""

    def test_configure_runtime_variable_resolved(self):
        """Verify RELEASE_TAG is resolved to its actual value in runtime.cfg.

        Bug 1: same chained expansion bug — DEPLOY_MANIFEST contains $RELEASE_TAG
        which only appears after ${DEPLOY_MANIFEST} expansion. The second pass must
        search the expanded result, not the original template.
        """
        output = _load_output("/app/output_eval_2.json")
        result = output["results"]["configure-runtime"]
        commands = result.get("commands", [])
        runtime_cmds = [c for c in commands if "runtime.cfg" in c.get("command", "")]
        assert len(runtime_cmds) > 0, "No runtime.cfg command found in configure-runtime"

        cmd = runtime_cmds[0]["command"]
        assert "deploy-9.1.0" in cmd, (
            f"RELEASE_TAG not resolved in runtime.cfg command: '{cmd}'. "
            f"Expected 'deploy-9.1.0'."
        )
        assert "release=9.1.0" in cmd, (
            f"VERSION not expanded in runtime.cfg command: '{cmd}'. "
            f"Expected 'release=9.1.0'."
        )
        assert "$RELEASE_TAG" not in cmd, (
            f"Unresolved '$RELEASE_TAG' in command: '{cmd}'."
        )


class TestEval2RetryState:
    """Tests for retry state management bug on eval taskfile 2."""

    def test_configure_runtime_retry_occurred(self):
        """Verify a retry occurred during configure-runtime on second eval taskfile."""
        output = _load_output("/app/output_eval_2.json")
        result = output["results"]["configure-runtime"]
        commands = result.get("commands", [])
        lock_cmds = [
            c for c in commands
            if ".lock" in c.get("command", "") and "test -f" in c.get("command", "")
        ]
        assert len(lock_cmds) >= 2, (
            f"Expected at least 2 retry-trigger commands, found {len(lock_cmds)}."
        )
        assert lock_cmds[0]["exit_code"] == 1, (
            f"First .lock check should fail, got {lock_cmds[0]['exit_code']}"
        )
        assert lock_cmds[1]["exit_code"] == 0, (
            f"Second .lock check should succeed, got {lock_cmds[1]['exit_code']}"
        )
