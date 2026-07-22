"""Verify SAUTH packet verification results."""
import json
from pathlib import Path

PRODUCED = Path("/app/results.json")
EXPECTED = Path("/tests/expected_output.json")


def test_output_exists():
    """Results file exists and is a JSON array."""
    assert PRODUCED.exists(), "/app/results.json not found"
    assert isinstance(json.loads(PRODUCED.read_text()), list)


def test_packet_count():
    """Correct number of results."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    assert len(got) == len(want), f"got {len(got)} results, want {len(want)}"


def test_validity():
    """Each packet's valid/invalid status matches expected."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    errors = []
    for i, (g, w) in enumerate(zip(got, want)):
        if g.get("valid") != w["valid"]:
            errors.append(f"packet {i}: got valid={g.get('valid')}, want {w['valid']}")
    assert not errors, "; ".join(errors)


def test_reasons():
    """Each packet's reason matches expected."""
    got = json.loads(PRODUCED.read_text())
    want = json.loads(EXPECTED.read_text())
    errors = []
    for i, (g, w) in enumerate(zip(got, want)):
        if g.get("reason") != w["reason"]:
            errors.append(f"packet {i}: got reason={g.get('reason')!r}, want {w['reason']!r}")
    assert not errors, "; ".join(errors)
