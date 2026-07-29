"""Tests for the Pebble interpreter."""
import json
import subprocess
from pathlib import Path

INTERP = Path("/app/pebble")
PROGRAMS = Path("/app/programs")
HIDDEN = Path("/tests/hidden_programs")
EXPECTED = json.loads(Path("/tests/expected_outputs.json").read_text())


def run_program(prog_path):
    r = subprocess.run([str(INTERP), str(prog_path)], capture_output=True, text=True, timeout=10)
    return r.stdout.rstrip("\n")


def test_interpreter_exists():
    """Criterion 1: /app/pebble exists and is executable."""
    assert INTERP.exists(), "/app/pebble not found"
    assert INTERP.stat().st_mode & 0o111, "/app/pebble is not executable"


def test_visible_programs():
    """Criterion 2: all visible test programs produce correct output."""
    for name in sorted(EXPECTED):
        if (PROGRAMS / name).exists():
            actual = run_program(PROGRAMS / name)
            assert actual == EXPECTED[name], f"{name}: expected {EXPECTED[name]!r}, got {actual!r}"


def test_hidden_programs():
    """Criterion 3: held-out programs verify correctness on additional cases."""
    for name in sorted(EXPECTED):
        if (HIDDEN / name).exists():
            actual = run_program(HIDDEN / name)
            assert actual == EXPECTED[name], f"{name}: expected {EXPECTED[name]!r}, got {actual!r}"
