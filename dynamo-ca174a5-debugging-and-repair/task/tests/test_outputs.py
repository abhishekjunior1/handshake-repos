"""Verify pipeline execution log matches expected output."""
import json
from pathlib import Path

PRODUCED = Path("/app/execution_log.json")
EXPECTED = Path("/tests/expected_output.json")

def test_output_exists():
    """Execution log exists and is a JSON array."""
    assert PRODUCED.exists(), "/app/execution_log.json not found"
    assert isinstance(json.loads(PRODUCED.read_text()), list)

def test_stage_count():
    """Correct number of stages executed."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    assert len(got) == len(want), f"got {len(got)} stages, want {len(want)}"

def test_execution_order():
    """Stages executed in correct order with correct execution_order values."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    got_names = [(s["stage_name"], s["execution_order"]) for s in got]
    want_names = [(s["stage_name"], s["execution_order"]) for s in want]
    assert got_names == want_names, f"order: got {got_names}, want {want_names}"

def test_output_states():
    """Output states match for all stages."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    errors = []
    for g, w in zip(got, want):
        if g.get("output_state") != w["output_state"]:
            errors.append(f"{w['stage_name']}: got {g.get('output_state')}, want {w['output_state']}")
    assert not errors, "; ".join(errors)

def test_statuses():
    """Stage statuses match."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    errors = []
    for g, w in zip(got, want):
        if g.get("status") != w["status"]:
            errors.append(f"{w['stage_name']}: got {g.get('status')}, want {w['status']}")
    assert not errors, "; ".join(errors)

def test_attempts():
    """Attempt counts match for all stages."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    errors = []
    for g, w in zip(got, want):
        if g.get("attempts") != w["attempts"]:
            errors.append(f"{w['stage_name']}: got attempts={g.get('attempts')}, want {w['attempts']}")
    assert not errors, "; ".join(errors)
