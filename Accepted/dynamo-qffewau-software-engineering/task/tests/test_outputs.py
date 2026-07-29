"""
Verification tests for the task execution pipeline output.
Checks that the agent produced correct output for both eval taskfiles.
The agent was instructed to run the pipeline on all eval taskfiles before submission.

Anti-cheat design:
- Two eval configs produce structurally different outputs (different task names, different
  parallel task prefixes, different variable names/versions) so hardcoding one fails the other.
- All asserted values are pipeline-computed outputs (command text, exit codes, task order)
  that can only be correct if the bugs were actually fixed and the pipeline was run.
- Expected outputs are sealed in /tests/ and never accessible to the agent.
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


# ── Existence checks ──────────────────────────────────────────────────────────

def test_eval1_output_exists():
    """The agent must produce /app/output_eval_1.json."""
    assert os.path.exists("/app/output_eval_1.json"), "output_eval_1.json not found"


def test_eval2_output_exists():
    """The agent must produce /app/output_eval_2.json."""
    assert os.path.exists("/app/output_eval_2.json"), "output_eval_2.json not found"


# ── Cross-config structural diversity ─────────────────────────────────────────

class TestCrossConfigDiversity:
    """Tests proving the two outputs are structurally different and cannot be hardcoded.

    Eval 1 (build pipeline): parallel tasks prefixed build-*, setup-env retries on .attempt,
    variable ARTIFACT_TAG resolved from DEPLOY_TEMPLATE containing $VERSION/$ARTIFACT_TAG.

    Eval 2 (deploy pipeline): parallel tasks prefixed deploy-*, configure-runtime retries
    on .lock, variable RELEASE_TAG resolved from DEPLOY_MANIFEST containing $VERSION/$RELEASE_TAG.

    Hardcoding eval 1's task names fails eval 2's name checks and vice versa.
    Hardcoding eval 1's resolved value ('release-3.2.1') fails eval 2's check ('deploy-9.1.0').
    """

    def test_parallel_task_prefixes_differ(self):
        """Eval 1 has build-* parallel tasks; eval 2 has deploy-* parallel tasks."""
        out1 = _load_output("/app/output_eval_1.json")
        out2 = _load_output("/app/output_eval_2.json")
        build_tasks = [t for t in out1["tasks_executed"] if t.startswith("build-")]
        deploy_tasks = [t for t in out2["tasks_executed"] if t.startswith("deploy-")]
        assert len(build_tasks) == 3, f"Eval 1 must have 3 build-* tasks, got {build_tasks}"
        assert len(deploy_tasks) == 3, f"Eval 2 must have 3 deploy-* tasks, got {deploy_tasks}"
        assert set(build_tasks) != set(deploy_tasks), "Parallel task sets must differ between configs"

    def test_retry_trigger_files_differ(self):
        """Eval 1 uses .attempt as retry trigger; eval 2 uses .lock."""
        out1 = _load_output("/app/output_eval_1.json")
        out2 = _load_output("/app/output_eval_2.json")
        # Eval 1 setup-env has .attempt retry
        cmds1 = out1["results"]["setup-env"]["commands"]
        attempt_cmds = [c for c in cmds1 if ".attempt" in c.get("command", "")]
        assert len(attempt_cmds) >= 2, "Eval 1 must show .attempt retry commands"
        # Eval 2 configure-runtime has .lock retry
        cmds2 = out2["results"]["configure-runtime"]["commands"]
        lock_cmds = [c for c in cmds2 if ".lock" in c.get("command", "")]
        assert len(lock_cmds) >= 2, "Eval 2 must show .lock retry commands"

    def test_resolved_variable_values_differ(self):
        """Eval 1 resolves to 'release-3.2.1'; eval 2 resolves to 'deploy-9.1.0'."""
        out1 = _load_output("/app/output_eval_1.json")
        out2 = _load_output("/app/output_eval_2.json")
        # Find the resolved variable command in eval 1
        cmds1 = out1["results"]["setup-env"]["commands"]
        write_cmds1 = [c for c in cmds1 if "build_vars.sh" in c.get("command", "")]
        assert len(write_cmds1) > 0, "Eval 1 must have build_vars.sh command"
        assert "release-3.2.1" in write_cmds1[0]["command"], \
            "Eval 1 must resolve ARTIFACT_TAG to 'release-3.2.1'"
        # Find the resolved variable command in eval 2
        cmds2 = out2["results"]["configure-runtime"]["commands"]
        write_cmds2 = [c for c in cmds2 if "runtime.cfg" in c.get("command", "")]
        assert len(write_cmds2) > 0, "Eval 2 must have runtime.cfg command"
        assert "deploy-9.1.0" in write_cmds2[0]["command"], \
            "Eval 2 must resolve RELEASE_TAG to 'deploy-9.1.0'"
        # The resolved values must be different (hardcoding one fails the other)
        assert "release-3.2.1" not in write_cmds2[0]["command"], \
            "Eval 2 must not contain eval 1's resolved value"
        assert "deploy-9.1.0" not in write_cmds1[0]["command"], \
            "Eval 1 must not contain eval 2's resolved value"

    def test_task_name_sets_disjoint(self):
        """The two configs execute completely different task name sets."""
        out1 = _load_output("/app/output_eval_1.json")
        out2 = _load_output("/app/output_eval_2.json")
        names1 = set(out1["tasks_executed"])
        names2 = set(out2["tasks_executed"])
        overlap = names1 & names2
        assert len(overlap) == 0, \
            f"Task names must be disjoint between configs, overlap: {overlap}"


# ── Eval 1: pipeline-computed values ─────────────────────────────────────────

class TestEval1PipelineOutput:
    """Tests for eval taskfile 1 pipeline-computed outputs.

    All assertions check values produced by the running pipeline, not values
    readable from the input taskfile. Specifically:
    - tasks_executed order (produced by the scheduler, wrong if Bug 2 unfixed)
    - .attempt retry exit codes (produced by executor retry logic, wrong if Bug 3 unfixed)
    - Fully-expanded command text (produced by variable expander, wrong if Bug 1 unfixed)
    """

    def test_pipeline_success(self):
        """Verify the pipeline completes successfully."""
        output = _load_output("/app/output_eval_1.json")
        assert output["success"] is True, \
            f"Pipeline failed: success={output.get('success')}"

    def test_exact_task_execution_order(self):
        """Verify exact task execution order matches expected sealed output.

        This catches Bug 2 (wrong scheduler function): with get_scheduled_groups()
        the parallel build tasks appear in priority order (build-worker, build-gateway,
        build-api) instead of alphabetical order (build-api, build-gateway, build-worker).
        Only the fixed get_parallelizable_groups() produces the correct sealed order.
        """
        output = _load_output("/app/output_eval_1.json")
        expected = _load_expected("expected_output.json")
        assert output["tasks_executed"] == expected["tasks_executed"], (
            f"Execution order mismatch.\n"
            f"  got:      {output['tasks_executed']}\n"
            f"  expected: {expected['tasks_executed']}"
        )

    def test_build_tasks_alphabetical_order(self):
        """Verify parallel build tasks appear alphabetically in tasks_executed.

        With parallelism=3 and sleep durations 0.3s/0.15s/0.05s, as_completed
        returns build-api last (slowest), build-worker first (fastest). Only
        get_parallelizable_groups() re-sorts by name after collection.
        """
        output = _load_output("/app/output_eval_1.json")
        executed = output["tasks_executed"]
        build_tasks = [t for t in executed if t.startswith("build-")]
        assert build_tasks == ["build-api", "build-gateway", "build-worker"], (
            f"Build task order: {build_tasks}, "
            f"expected alphabetical: ['build-api', 'build-gateway', 'build-worker']"
        )

    def test_setup_env_command_count(self):
        """Verify setup-env executed exactly 5 commands including retry.

        The retry adds one extra .attempt test command — without retry (Bug 3),
        only 4 commands appear. This count is pipeline-computed, not in the taskfile.
        """
        output = _load_output("/app/output_eval_1.json")
        expected = _load_expected("expected_output.json")
        out_cmds = output["results"]["setup-env"]["commands"]
        exp_cmds = expected["results"]["setup-env"]["commands"]
        assert len(out_cmds) == len(exp_cmds), (
            f"setup-env command count: got {len(out_cmds)}, expected {len(exp_cmds)}. "
            f"Retry must add exactly one extra command."
        )

    def test_setup_env_retry_exit_codes(self):
        """Verify .attempt retry shows exit_code=1 then exit_code=0.

        Bug 3: env rebuilt on retry loses captured ARTIFACT_TAG export.
        Without the fix, the retry succeeds structurally but the downstream
        command writes wrong content (unresolved variable). Both retry attempts
        must be present with the correct exit codes.
        """
        output = _load_output("/app/output_eval_1.json")
        cmds = output["results"]["setup-env"]["commands"]
        attempt_cmds = [
            c for c in cmds
            if ".attempt" in c.get("command", "") and "test -f" in c.get("command", "")
        ]
        assert len(attempt_cmds) >= 2, (
            f"Expected >=2 .attempt commands (retry), found {len(attempt_cmds)}"
        )
        assert attempt_cmds[0]["exit_code"] == 1, \
            f"First .attempt must fail (exit_code=1), got {attempt_cmds[0]['exit_code']}"
        assert attempt_cmds[1]["exit_code"] == 0, \
            f"Second .attempt must succeed (exit_code=0), got {attempt_cmds[1]['exit_code']}"

    def test_build_vars_command_fully_expanded(self):
        """Verify build_vars.sh command contains fully chain-expanded values.

        Bug 1: second-pass regex searches 'command' (original template) not 'result'
        (partially expanded). DEPLOY_TEMPLATE='artifact=$VERSION tag=$ARTIFACT_TAG'
        expands to 'artifact=3.2.1 tag=$ARTIFACT_TAG' in pass 1 (${VAR} substitution),
        then pass 2 must find $ARTIFACT_TAG in the RESULT to resolve it to 'release-3.2.1'.
        Without the fix, the command contains literal '$ARTIFACT_TAG'.
        """
        output = _load_output("/app/output_eval_1.json")
        cmds = output["results"]["setup-env"]["commands"]
        write_cmds = [c for c in cmds if "build_vars.sh" in c.get("command", "")]
        assert len(write_cmds) > 0, "No build_vars.sh write command found"
        cmd = write_cmds[0]["command"]
        assert "artifact=3.2.1" in cmd, \
            f"VERSION not expanded in build_vars.sh: '{cmd}'"
        assert "tag=release-3.2.1" in cmd, \
            f"ARTIFACT_TAG not chain-expanded in build_vars.sh: '{cmd}'"
        assert "$ARTIFACT_TAG" not in cmd, \
            f"Unresolved '$ARTIFACT_TAG' found in build_vars.sh: '{cmd}'"
        assert "$DEPLOY_TEMPLATE" not in cmd, \
            f"Unresolved '$DEPLOY_TEMPLATE' found in build_vars.sh: '{cmd}'"

    def test_variable_persists_after_retry(self):
        """Verify ARTIFACT_TAG export survives the retry boundary.

        Bug 3: env rebuild on retry loses exported variables. After the second
        .attempt succeeds, the build_vars.sh write command must still contain
        the resolved ARTIFACT_TAG value — proving env was preserved across retry.
        """
        output = _load_output("/app/output_eval_1.json")
        cmds = output["results"]["setup-env"]["commands"]
        # Find retry success index
        retry_idx = None
        count = 0
        for i, c in enumerate(cmds):
            if ".attempt" in c.get("command", "") and "test -f" in c.get("command", ""):
                count += 1
                if count == 2:
                    retry_idx = i
                    break
        assert retry_idx is not None, "Could not find second .attempt command"
        post_retry_text = " ".join(c.get("command", "") for c in cmds[retry_idx + 1:])
        assert "release-3.2.1" in post_retry_text, (
            f"ARTIFACT_TAG value 'release-3.2.1' not found after retry. "
            f"Variable lost across retry boundary."
        )

    def test_all_tasks_succeed(self):
        """Verify all tasks in eval 1 completed with status success."""
        output = _load_output("/app/output_eval_1.json")
        for name, result in output["results"].items():
            assert result["status"] == "success", \
                f"Task '{name}' has status '{result['status']}'"

    def test_setup_env_command_texts_match_expected(self):
        """Verify setup-env command texts match sealed expected output exactly.

        The setup-env task contains the three pipeline-computed values that prove
        all three bugs were fixed:
        - Command[0]: exported ARTIFACT_TAG value (Bug 1 variable expansion)
        - Command[1,2]: .attempt retry commands with exit codes (Bug 3 retry state)
        - Command[3]: fully chain-expanded build_vars.sh content (Bug 1 chained expansion)
        These are compared against the sealed expected fixture, not the input taskfile.
        """
        output = _load_output("/app/output_eval_1.json")
        expected = _load_expected("expected_output.json")
        out_cmds = output["results"]["setup-env"]["commands"]
        exp_cmds = expected["results"]["setup-env"]["commands"]
        assert len(out_cmds) == len(exp_cmds), \
            f"setup-env command count: got {len(out_cmds)}, expected {len(exp_cmds)}"
        for i, (oc, ec) in enumerate(zip(out_cmds, exp_cmds)):
            assert oc["command"] == ec["command"], \
                f"setup-env command[{i}] mismatch:\n  got: {oc['command']}\n  exp: {ec['command']}"
            assert oc["exit_code"] == ec["exit_code"], \
                f"setup-env command[{i}] exit_code: got {oc['exit_code']}, exp {ec['exit_code']}"


# ── Eval 2: pipeline-computed values ─────────────────────────────────────────

class TestEval2PipelineOutput:
    """Tests for eval taskfile 2 pipeline-computed outputs.

    Eval 2 uses a deploy pipeline with different service names, different variable
    names (RELEASE_TAG vs ARTIFACT_TAG), different version (9.1.0 vs 3.2.1),
    and a .lock retry trigger instead of .attempt. Hardcoding eval 1's answers
    fails every structural check here.
    """

    def test_pipeline_success(self):
        """Verify the pipeline completes successfully on eval taskfile 2."""
        output = _load_output("/app/output_eval_2.json")
        assert output["success"] is True, \
            f"Pipeline failed: success={output.get('success')}"

    def test_exact_task_execution_order(self):
        """Verify exact task execution order matches expected sealed output for eval 2."""
        output = _load_output("/app/output_eval_2.json")
        expected = _load_expected("expected_output_2.json")
        assert output["tasks_executed"] == expected["tasks_executed"], (
            f"Execution order mismatch.\n"
            f"  got:      {output['tasks_executed']}\n"
            f"  expected: {expected['tasks_executed']}"
        )

    def test_deploy_tasks_alphabetical_order(self):
        """Verify parallel deploy tasks appear alphabetically in tasks_executed.

        Same Bug 2 but different service names: deploy-auth, deploy-backend,
        deploy-proxy with sleep 0.25/0.1/0.2. Without fix: completion order
        is deploy-backend, deploy-proxy, deploy-auth (by speed).
        """
        output = _load_output("/app/output_eval_2.json")
        executed = output["tasks_executed"]
        deploy_tasks = [t for t in executed if t.startswith("deploy-")]
        assert deploy_tasks == ["deploy-auth", "deploy-backend", "deploy-proxy"], (
            f"Deploy task order: {deploy_tasks}, "
            f"expected alphabetical: ['deploy-auth', 'deploy-backend', 'deploy-proxy']"
        )

    def test_configure_runtime_command_count(self):
        """Verify configure-runtime executed the correct number of commands including retry."""
        output = _load_output("/app/output_eval_2.json")
        expected = _load_expected("expected_output_2.json")
        out_cmds = output["results"]["configure-runtime"]["commands"]
        exp_cmds = expected["results"]["configure-runtime"]["commands"]
        assert len(out_cmds) == len(exp_cmds), (
            f"configure-runtime command count: got {len(out_cmds)}, expected {len(exp_cmds)}"
        )

    def test_configure_runtime_retry_exit_codes(self):
        """Verify .lock retry shows exit_code=1 then exit_code=0."""
        output = _load_output("/app/output_eval_2.json")
        cmds = output["results"]["configure-runtime"]["commands"]
        lock_cmds = [
            c for c in cmds
            if ".lock" in c.get("command", "") and "test -f" in c.get("command", "")
        ]
        assert len(lock_cmds) >= 2, \
            f"Expected >=2 .lock commands (retry), found {len(lock_cmds)}"
        assert lock_cmds[0]["exit_code"] == 1, \
            f"First .lock must fail (exit_code=1), got {lock_cmds[0]['exit_code']}"
        assert lock_cmds[1]["exit_code"] == 0, \
            f"Second .lock must succeed (exit_code=0), got {lock_cmds[1]['exit_code']}"

    def test_runtime_cfg_command_fully_expanded(self):
        """Verify runtime.cfg command contains fully chain-expanded values.

        Same Bug 1 but different variable: DEPLOY_MANIFEST='release=$VERSION tag=$RELEASE_TAG'.
        Pass 1 expands ${DEPLOY_MANIFEST} → 'release=9.1.0 tag=$RELEASE_TAG'.
        Pass 2 must search the result to resolve $RELEASE_TAG → 'deploy-9.1.0'.
        Without the fix: literal '$RELEASE_TAG' appears in the command.
        """
        output = _load_output("/app/output_eval_2.json")
        cmds = output["results"]["configure-runtime"]["commands"]
        write_cmds = [c for c in cmds if "runtime.cfg" in c.get("command", "")]
        assert len(write_cmds) > 0, "No runtime.cfg write command found"
        cmd = write_cmds[0]["command"]
        assert "release=9.1.0" in cmd, \
            f"VERSION not expanded in runtime.cfg: '{cmd}'"
        assert "tag=deploy-9.1.0" in cmd, \
            f"RELEASE_TAG not chain-expanded in runtime.cfg: '{cmd}'"
        assert "$RELEASE_TAG" not in cmd, \
            f"Unresolved '$RELEASE_TAG' found in runtime.cfg: '{cmd}'"

    def test_variable_persists_after_retry(self):
        """Verify RELEASE_TAG export survives the retry boundary in eval 2."""
        output = _load_output("/app/output_eval_2.json")
        cmds = output["results"]["configure-runtime"]["commands"]
        retry_idx = None
        count = 0
        for i, c in enumerate(cmds):
            if ".lock" in c.get("command", "") and "test -f" in c.get("command", ""):
                count += 1
                if count == 2:
                    retry_idx = i
                    break
        assert retry_idx is not None, "Could not find second .lock command"
        post_retry_text = " ".join(c.get("command", "") for c in cmds[retry_idx + 1:])
        assert "deploy-9.1.0" in post_retry_text, (
            f"RELEASE_TAG value 'deploy-9.1.0' not found after retry. "
            f"Variable lost across retry boundary."
        )

    def test_all_tasks_succeed(self):
        """Verify all tasks in eval 2 completed with status success."""
        output = _load_output("/app/output_eval_2.json")
        for name, result in output["results"].items():
            assert result["status"] == "success", \
                f"Task '{name}' has status '{result['status']}'"

    def test_configure_runtime_command_texts_match_expected(self):
        """Verify configure-runtime command texts match sealed expected output exactly.

        Same principle as eval 1: only the configure-runtime task contains the
        pipeline-computed values (variable expansion + retry exit codes) that
        prove all three bugs were fixed on this config.
        """
        output = _load_output("/app/output_eval_2.json")
        expected = _load_expected("expected_output_2.json")
        out_cmds = output["results"]["configure-runtime"]["commands"]
        exp_cmds = expected["results"]["configure-runtime"]["commands"]
        assert len(out_cmds) == len(exp_cmds), \
            f"configure-runtime command count: got {len(out_cmds)}, expected {len(exp_cmds)}"
        for i, (oc, ec) in enumerate(zip(out_cmds, exp_cmds)):
            assert oc["command"] == ec["command"], \
                f"configure-runtime command[{i}] mismatch:\n  got: {oc['command']}\n  exp: {ec['command']}"
            assert oc["exit_code"] == ec["exit_code"], \
                f"configure-runtime command[{i}] exit_code: got {oc['exit_code']}, exp {ec['exit_code']}"
