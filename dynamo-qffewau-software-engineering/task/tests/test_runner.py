"""
Unit-level tests that validate task runner internals.
These run in addition to the integration tests in test_outputs.py.
"""
import json
import os
import subprocess
import sys


HIDDEN_TASKFILE = "/tests/hidden_taskfile.json"
HIDDEN_OUTPUT = "/tmp/hidden_output.json"


def _ensure_hidden_run():
    if not os.path.exists(HIDDEN_OUTPUT):
        subprocess.run(
            [sys.executable, "/app/runner.py", HIDDEN_TASKFILE, HIDDEN_OUTPUT],
            cwd="/app",
            capture_output=True,
            text=True,
            timeout=60,
        )


def test_hidden_setup_env_retried_successfully():
    """The setup-env task must succeed despite initial failure (retry works)."""
    _ensure_hidden_run()
    with open(HIDDEN_OUTPUT) as f:
        data = json.load(f)
    results = data.get("results", {})
    setup = results.get("setup-env", {})
    assert setup.get("status") == "success"
    commands = setup.get("commands", [])
    assert len(commands) >= 4, (
        f"Expected retry attempts in command log, got {len(commands)} commands"
    )


def test_hidden_build_outputs_exist():
    """All build outputs must be created by the parallel build tasks."""
    _ensure_hidden_run()
    with open(HIDDEN_OUTPUT) as f:
        data = json.load(f)
    results = data.get("results", {})
    for svc in ["build-api", "build-worker", "build-gateway"]:
        assert svc in results, f"Missing result for {svc}"
        assert results[svc]["status"] == "success", f"{svc} failed"


def test_hidden_package_postcondition():
    """Package task postcondition must pass - release archive created."""
    _ensure_hidden_run()
    with open(HIDDEN_OUTPUT) as f:
        data = json.load(f)
    results = data.get("results", {})
    pkg = results.get("package", {})
    assert pkg.get("status") == "success", f"package failed: {pkg}"
