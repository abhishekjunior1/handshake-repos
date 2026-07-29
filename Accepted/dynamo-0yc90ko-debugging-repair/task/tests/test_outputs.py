"""Verify event processor output."""
import json
from pathlib import Path

PRODUCED = Path("/app/summary.json")
EXPECTED = Path("/tests/expected_output.json")

def test_output_exists():
    """Output exists and is valid JSON."""
    assert PRODUCED.exists()
    assert isinstance(json.loads(PRODUCED.read_text()), dict)

def test_categories():
    """Same categories present."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    assert set(got.keys()) == set(want.keys()), f"categories: got {set(got.keys())}, want {set(want.keys())}"

def test_scores():
    """All score values match exactly."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    errors = []
    for cat in want:
        gw = got.get(cat, [])
        ww = want[cat]
        if len(gw) != len(ww):
            errors.append(f"{cat}: got {len(gw)} windows, want {len(ww)}")
            continue
        for i, (g, w) in enumerate(zip(gw, ww)):
            for field in ["count", "total_score", "max_score"]:
                if field in w and g.get(field) != w[field]:
                    errors.append(f"{cat}[{i}].{field}: got {g.get(field)} want {w[field]}")
    assert not errors, "; ".join(errors[:5])
