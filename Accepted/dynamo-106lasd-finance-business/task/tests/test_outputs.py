"""Verify cashflow engine produces correct distributions."""
import json
from pathlib import Path

PRODUCED = Path("/app/distributions.json")
EXPECTED = Path("/tests/expected_output.json")

def _p(): return json.loads(PRODUCED.read_text())
def _e(): return json.loads(EXPECTED.read_text())

def test_output_exists():
    """Output exists and is a JSON array."""
    assert PRODUCED.exists(), "/app/distributions.json not found"
    assert isinstance(_p(), list), "must be a JSON array"

def test_month_count():
    """Correct number of months."""
    assert len(_p()) == len(_e()), f"got {len(_p())} months, want {len(_e())}"

def test_balances():
    """Ending balances match for all tranches across all months."""
    got, want = _p(), _e()
    errors = []
    for i, (g, w) in enumerate(zip(got, want)):
        for tname in w["tranches"]:
            gb = g.get("tranches", {}).get(tname, {}).get("ending_balance")
            wb = w["tranches"][tname]["ending_balance"]
            if gb != wb:
                errors.append(f"month {w['month']} {tname}: balance got {gb} want {wb}")
    assert not errors, "; ".join(errors[:5])

def test_amounts():
    """Interest, principal, and loss amounts match exactly."""
    got, want = _p(), _e()
    errors = []
    for i, (g, w) in enumerate(zip(got, want)):
        for tname in w["tranches"]:
            gt = g.get("tranches", {}).get(tname, {})
            wt = w["tranches"][tname]
            for field in ["interest_paid", "principal_paid", "loss_allocated"]:
                if gt.get(field) != wt[field]:
                    errors.append(f"month {w['month']} {tname} {field}: got {gt.get(field)} want {wt[field]}")
    assert not errors, "; ".join(errors[:5])
