"""
Verification tests for the cryptographic envelope pipeline.

Compares the agent's output against the expected output generated
by the correct pipeline on the hidden test configuration.
"""

import json
from pathlib import Path


EXPECTED_PATH = Path("/tests/expected_output.json")
OUTPUT_PATH = Path("/app/output.json")


def _load_expected():
    """Load the expected output from the test fixtures."""
    return json.loads(EXPECTED_PATH.read_text())


def _load_output():
    """Load the agent's output."""
    return json.loads(OUTPUT_PATH.read_text())


def test_output_file_exists():
    """The pipeline must produce /app/output.json."""
    assert OUTPUT_PATH.exists(), "output.json was not created"


def test_output_valid_json():
    """The output must be valid JSON."""
    text = OUTPUT_PATH.read_text()
    data = json.loads(text)
    assert isinstance(data, dict), "Output must be a JSON object"


def test_pipeline_version():
    """The output must report the correct pipeline version."""
    output = _load_output()
    expected = _load_expected()
    assert output.get("pipeline_version") == expected["pipeline_version"], \
        "Pipeline version mismatch"


def test_num_messages():
    """The output must contain the correct number of processed messages."""
    output = _load_output()
    expected = _load_expected()
    assert output.get("num_messages") == expected["num_messages"], \
        f"Expected {expected['num_messages']} messages, got {output.get('num_messages')}"


def test_key_derivation_fingerprints():
    """The key derivation must produce correct encryption and MAC key fingerprints."""
    output = _load_output()
    expected = _load_expected()
    assert output.get("key_derivation") == expected["key_derivation"], \
        f"Key fingerprints differ: got {output.get('key_derivation')}, expected {expected['key_derivation']}"


def test_envelope_count():
    """The correct number of envelopes must be present in the output."""
    output = _load_output()
    expected = _load_expected()
    assert len(output.get("envelopes", [])) == len(expected["envelopes"]), \
        "Envelope count mismatch"


def test_message_ids_match():
    """All expected message IDs must appear in the output."""
    output = _load_output()
    expected = _load_expected()
    output_ids = {e["message_id"] for e in output.get("envelopes", [])}
    expected_ids = {e["message_id"] for e in expected["envelopes"]}
    assert output_ids == expected_ids, \
        f"Message ID mismatch: got {output_ids}, expected {expected_ids}"


def test_envelope_alpha_exact():
    """The first envelope (secure_msg_alpha) must match expected output exactly."""
    output = _load_output()
    expected = _load_expected()
    out_env = next(e for e in output["envelopes"] if e["message_id"] == "secure_msg_alpha")
    exp_env = next(e for e in expected["envelopes"] if e["message_id"] == "secure_msg_alpha")
    assert out_env["envelope_hex"] == exp_env["envelope_hex"], \
        "Envelope alpha hex content differs"
    assert out_env["mac_tag_hex"] == exp_env["mac_tag_hex"], \
        "Envelope alpha MAC tag differs"


def test_envelope_beta_exact():
    """The second envelope (secure_msg_beta) must match expected output exactly."""
    output = _load_output()
    expected = _load_expected()
    out_env = next(e for e in output["envelopes"] if e["message_id"] == "secure_msg_beta")
    exp_env = next(e for e in expected["envelopes"] if e["message_id"] == "secure_msg_beta")
    assert out_env["envelope_hex"] == exp_env["envelope_hex"], \
        "Envelope beta hex content differs"
    assert out_env["mac_tag_hex"] == exp_env["mac_tag_hex"], \
        "Envelope beta MAC tag differs"


def test_envelope_gamma_exact():
    """The third envelope (secure_msg_gamma) must match expected output exactly."""
    output = _load_output()
    expected = _load_expected()
    out_env = next(e for e in output["envelopes"] if e["message_id"] == "secure_msg_gamma")
    exp_env = next(e for e in expected["envelopes"] if e["message_id"] == "secure_msg_gamma")
    assert out_env["envelope_hex"] == exp_env["envelope_hex"], \
        "Envelope gamma hex content differs"
    assert out_env["mac_tag_hex"] == exp_env["mac_tag_hex"], \
        "Envelope gamma MAC tag differs"


def test_ciphertext_lengths():
    """All ciphertext lengths must match expected values."""
    output = _load_output()
    expected = _load_expected()
    for exp_env in expected["envelopes"]:
        msg_id = exp_env["message_id"]
        out_env = next((e for e in output["envelopes"] if e["message_id"] == msg_id), None)
        assert out_env is not None, f"Missing envelope for {msg_id}"
        assert out_env["ciphertext_length"] == exp_env["ciphertext_length"], \
            f"Ciphertext length mismatch for {msg_id}"


def test_envelope_digests():
    """All envelope SHA-256 digests must match expected values."""
    output = _load_output()
    expected = _load_expected()
    for exp_env in expected["envelopes"]:
        msg_id = exp_env["message_id"]
        out_env = next((e for e in output["envelopes"] if e["message_id"] == msg_id), None)
        assert out_env is not None, f"Missing envelope for {msg_id}"
        assert out_env["envelope_digest"] == exp_env["envelope_digest"], \
            f"Envelope digest mismatch for {msg_id}: got {out_env['envelope_digest']}, expected {exp_env['envelope_digest']}"


def test_envelope_sizes():
    """All envelope sizes must match expected values."""
    output = _load_output()
    expected = _load_expected()
    for exp_env in expected["envelopes"]:
        msg_id = exp_env["message_id"]
        out_env = next((e for e in output["envelopes"] if e["message_id"] == msg_id), None)
        assert out_env is not None, f"Missing envelope for {msg_id}"
        assert out_env["envelope_size"] == exp_env["envelope_size"], \
            f"Envelope size mismatch for {msg_id}: got {out_env['envelope_size']}, expected {exp_env['envelope_size']}"


def test_per_envelope_fingerprints():
    """Each envelope must report correct enc_key and mac_key fingerprints."""
    output = _load_output()
    expected = _load_expected()
    for exp_env in expected["envelopes"]:
        msg_id = exp_env["message_id"]
        out_env = next((e for e in output["envelopes"] if e["message_id"] == msg_id), None)
        assert out_env is not None, f"Missing envelope for {msg_id}"
        assert out_env["enc_key_fingerprint"] == exp_env["enc_key_fingerprint"], \
            f"enc_key_fingerprint mismatch for {msg_id}"
        assert out_env["mac_key_fingerprint"] == exp_env["mac_key_fingerprint"], \
            f"mac_key_fingerprint mismatch for {msg_id}"


def test_sender_recipient():
    """Each envelope must report correct sender and recipient fields."""
    output = _load_output()
    expected = _load_expected()
    for exp_env in expected["envelopes"]:
        msg_id = exp_env["message_id"]
        out_env = next((e for e in output["envelopes"] if e["message_id"] == msg_id), None)
        assert out_env is not None, f"Missing envelope for {msg_id}"
        assert out_env["sender"] == exp_env["sender"], \
            f"Sender mismatch for {msg_id}"
        assert out_env["recipient"] == exp_env["recipient"], \
            f"Recipient mismatch for {msg_id}"
