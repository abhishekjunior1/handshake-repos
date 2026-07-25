"""Crypto Reporter — formats pipeline output to structured JSON.

Produces the final output report with hex-encoded cryptographic values,
verification results, envelope structure, and pipeline metadata.
"""


def _compute_security_level(metadata):
    """Compute the effective security level in bits."""
    key_bits = metadata['key_length_bytes'] * 8
    rsa_bits = metadata['rsa_key_bits']
    rsa_security = {2048: 112, 3072: 128, 4096: 152}
    rsa_level = rsa_security.get(rsa_bits, 112)
    hash_security = {'SHA-256': 128, 'SHA-384': 192, 'SHA-512': 256}
    hash_level = hash_security.get(metadata['kdf_hash'], 128)
    return min(key_bits, rsa_level, hash_level)


def format_report(results):
    """Format pipeline results into the output report structure."""
    encryption = results['encryption']
    verification = results['verification']
    envelope = results['envelope']
    metadata = results['metadata']

    security_level = _compute_security_level(metadata)

    report = {
        'pipeline_output': {
            'encryption_results': {
                'shared_secret': encryption['shared_secret_hex'],
                'derived_key': encryption['derived_key_hex'],
                'derived_key_length_bytes': encryption['derived_key_length'],
                'ciphertext': encryption['ciphertext_hex'],
                'nonce': encryption['nonce_hex'],
                'gcm_tag': encryption['gcm_tag_hex'],
                'hmac_tag': encryption['hmac_tag_hex'],
                'mac_key': encryption['mac_key_hex'],
                'key_check_value': encryption['key_check_value_hex'],
            },
            'verification_results': {
                'decryption_success': verification['decryption_successful'],
                'mac_verification': verification['mac_valid'],
                'key_agreement_valid': verification['key_agreement_valid'],
                'round_trip_text': verification['decrypted_text'],
            },
            'envelope': envelope,
            'security_assessment': {
                'cipher_suite': metadata['cipher_suite'],
                'effective_security_bits': security_level,
                'key_length_bytes': metadata['key_length_bytes'],
                'nonce_bits': metadata['nonce_bits'],
                'kdf_algorithm': f"HKDF-{metadata['kdf_hash']}",
                'mac_algorithm': metadata['mac_algorithm'],
                'rsa_key_bits': metadata['rsa_key_bits'],
                'compliance': {
                    'nist_approved_algorithms': True,
                    'minimum_112_bit_security': security_level >= 112,
                    'authenticated_encryption': True,
                    'key_derivation_standard': 'RFC 5869',
                    'nonce_generation': 'deterministic-synthetic-iv',
                    'gcm_nonce_96_bit': metadata['nonce_bits'] == 96,
                },
            },
        }
    }

    return report
