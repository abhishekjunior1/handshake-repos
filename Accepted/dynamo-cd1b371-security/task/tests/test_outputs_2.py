"""Test suite for hybrid encryption pipeline — configuration 2 (AES-192-GCM).

Validates pipeline output against expected values for a configuration using
AES-192-GCM with distinct HKDF salt/info and non-empty AAD.
"""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def pipeline_output():
    """Load the pipeline output from /app/output.json."""
    with open("/app/output.json") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected output for hidden_input_2 configuration."""
    with open(os.path.join(TESTS_DIR, "expected_output_2.json")) as f:
        return json.load(f)


class TestEncryptionResults:
    """Tests for encryption output correctness."""

    def test_derived_key_length(self, pipeline_output, expected_output):
        """Verify derived key length matches the cipher suite requirement."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["derived_key_length_bytes"]
        expected = expected_output["pipeline_output"]["encryption_results"]["derived_key_length_bytes"]
        assert actual == expected, f"Key length mismatch: got {actual}, expected {expected}"

    def test_derived_key_value(self, pipeline_output, expected_output):
        """Verify derived key hex matches expected HKDF output."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["derived_key"]
        expected = expected_output["pipeline_output"]["encryption_results"]["derived_key"]
        assert actual == expected, f"Derived key mismatch"

    def test_ciphertext(self, pipeline_output, expected_output):
        """Verify ciphertext matches expected AES-GCM encryption output."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["ciphertext"]
        expected = expected_output["pipeline_output"]["encryption_results"]["ciphertext"]
        assert actual == expected, f"Ciphertext mismatch"

    def test_nonce(self, pipeline_output, expected_output):
        """Verify nonce matches expected deterministic value."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["nonce"]
        expected = expected_output["pipeline_output"]["encryption_results"]["nonce"]
        assert actual == expected, f"Nonce mismatch"

    def test_gcm_tag(self, pipeline_output, expected_output):
        """Verify GCM authentication tag matches expected value."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["gcm_tag"]
        expected = expected_output["pipeline_output"]["encryption_results"]["gcm_tag"]
        assert actual == expected, f"GCM tag mismatch"

    def test_hmac_tag(self, pipeline_output, expected_output):
        """Verify HMAC envelope tag matches expected value including AAD coverage."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["hmac_tag"]
        expected = expected_output["pipeline_output"]["encryption_results"]["hmac_tag"]
        assert actual == expected, f"HMAC tag mismatch"

    def test_mac_key(self, pipeline_output, expected_output):
        """Verify MAC key derivation produces expected key material."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["mac_key"]
        expected = expected_output["pipeline_output"]["encryption_results"]["mac_key"]
        assert actual == expected, f"MAC key mismatch"

    def test_key_check_value(self, pipeline_output, expected_output):
        """Verify key check value matches expected binding confirmation."""
        actual = pipeline_output["pipeline_output"]["encryption_results"]["key_check_value"]
        expected = expected_output["pipeline_output"]["encryption_results"]["key_check_value"]
        assert actual == expected, f"Key check value mismatch"


class TestVerificationResults:
    """Tests for pipeline verification correctness."""

    def test_decryption_success(self, pipeline_output, expected_output):
        """Verify decryption round-trip succeeds."""
        actual = pipeline_output["pipeline_output"]["verification_results"]["decryption_success"]
        expected = expected_output["pipeline_output"]["verification_results"]["decryption_success"]
        assert actual == expected

    def test_mac_verification(self, pipeline_output, expected_output):
        """Verify MAC verification passes."""
        actual = pipeline_output["pipeline_output"]["verification_results"]["mac_verification"]
        expected = expected_output["pipeline_output"]["verification_results"]["mac_verification"]
        assert actual == expected

    def test_key_agreement(self, pipeline_output, expected_output):
        """Verify key agreement between KEM encapsulation and decapsulation."""
        actual = pipeline_output["pipeline_output"]["verification_results"]["key_agreement_valid"]
        expected = expected_output["pipeline_output"]["verification_results"]["key_agreement_valid"]
        assert actual == expected


class TestSecurityAssessment:
    """Tests for security metadata correctness."""

    def test_cipher_suite(self, pipeline_output, expected_output):
        """Verify cipher suite matches configuration."""
        actual = pipeline_output["pipeline_output"]["security_assessment"]["cipher_suite"]
        expected = expected_output["pipeline_output"]["security_assessment"]["cipher_suite"]
        assert actual == expected

    def test_key_length_bytes(self, pipeline_output, expected_output):
        """Verify reported key length matches cipher suite requirement."""
        actual = pipeline_output["pipeline_output"]["security_assessment"]["key_length_bytes"]
        expected = expected_output["pipeline_output"]["security_assessment"]["key_length_bytes"]
        assert actual == expected

    def test_nonce_bits(self, pipeline_output, expected_output):
        """Verify nonce bit length is 96 (NIST SP 800-38D standard)."""
        actual = pipeline_output["pipeline_output"]["security_assessment"]["nonce_bits"]
        expected = expected_output["pipeline_output"]["security_assessment"]["nonce_bits"]
        assert actual == expected

    def test_effective_security_bits(self, pipeline_output, expected_output):
        """Verify effective security level computation."""
        actual = pipeline_output["pipeline_output"]["security_assessment"]["effective_security_bits"]
        expected = expected_output["pipeline_output"]["security_assessment"]["effective_security_bits"]
        assert actual == expected
