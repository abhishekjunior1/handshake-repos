"""Shared loaders and comparison helpers for the hidden-config test modules.

Outputs and expected values come from the 0700 staging directory the harness
writes, never from /app or /tests, so nothing the submission can reach feeds
the assertions.
"""

import json
import os
from pathlib import Path


def _verify_dir():
    """Locate the staging dir the harness chose, trying the same order it did."""
    override = os.environ.get("DMA_VERIFY_DIR")
    candidates = [Path(override)] if override else [
        Path("/opt/dma_verify"), Path.home() / ".dma_verify", Path("/tmp/.dma_verify")]
    for candidate in candidates:
        if (candidate / "status.json").is_file():
            return candidate
    raise AssertionError(
        "verifier harness produced no staging directory — it did not complete")


def _read_json(path):
    """Read a staged JSON file, refusing to traverse a symlink to get there."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    with os.fdopen(fd, "r") as handle:
        return json.load(handle)


def harness_status():
    """Return the harness's full record of the graded run."""
    return _read_json(_verify_dir() / "status.json")


def run_status(config_index):
    """Return the harness's record of the pipeline run for one hidden config."""
    return harness_status()["runs"][str(config_index)]


def load_output(config_index):
    """Load the guarded pipeline output captured for one hidden config."""
    return _read_json(_verify_dir() / f"actual_{config_index}.json")


def load_expected(config_index):
    """Load the expected output for one hidden config."""
    return _read_json(_verify_dir() / f"expected_{config_index}.json")


def load_config(config_index):
    """Load the hidden config the pipeline was run on, for derived checks."""
    return _read_json(_verify_dir() / f"config_{config_index}.json")


def strict_diff(actual, expected, path="output"):
    """Return the first type-or-value mismatch between two JSON trees, or None.

    Types are compared exactly so that Python's ``True == 1`` equivalence cannot
    let a boolean flag pass where an integer count is required, or vice versa.
    """
    if type(actual) is not type(expected):
        return f"{path}: expected {type(expected).__name__} {expected!r}, got {type(actual).__name__} {actual!r}"
    if isinstance(expected, dict):
        missing = sorted(set(expected) - set(actual))
        if missing:
            return f"{path}: missing key(s) {missing}"
        extra = sorted(set(actual) - set(expected))
        if extra:
            return f"{path}: unexpected key(s) {extra}"
        for key in expected:
            found = strict_diff(actual[key], expected[key], f"{path}.{key}")
            if found:
                return found
        return None
    if isinstance(expected, list):
        if len(actual) != len(expected):
            return f"{path}: expected {len(expected)} entries, got {len(actual)}"
        for i, (a, e) in enumerate(zip(actual, expected)):
            found = strict_diff(a, e, f"{path}[{i}]")
            if found:
                return found
        return None
    if actual != expected:
        return f"{path}: expected {expected!r}, got {actual!r}"
    return None
