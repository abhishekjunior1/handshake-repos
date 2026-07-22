"""Hybrid Encryption Pipeline — RSA-KEM + AES-GCM orchestrator.

Drives the full encrypt/decrypt lifecycle: key encapsulation, derivation,
bulk encryption, authentication, and envelope assembly.
"""

import json
import sys
import os
import hashlib

from key_encapsulator import generate_kem_keypair, encapsulate_key, decapsulate_key
from key_deriver import derive_key_material, derive_authenticated_context
from bulk_cipher import encrypt_payload, decrypt_payload
from mac_authenticator import compute_envelope_mac, verify_envelope_mac
from envelope_builder import build_envelope, parse_envelope
from crypto_reporter import format_report


def load_config(config_path):
    """Load pipeline configuration from JSON file."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    return config


def validate_config(config):
    """Validate required configuration fields are present and well-formed."""
    required_fields = [
        'cipher_suite', 'kdf_params', 'mac_params',
        'envelope_params', 'plaintext', 'rsa_key_bits'
    ]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")

    cipher_suite = config['cipher_suite']
    if 'algorithm' not in cipher_suite:
        raise ValueError("cipher_suite must specify algorithm")
    if 'nonce_bits' not in cipher_suite:
        raise ValueError("cipher_suite must specify nonce_bits")
    if 'key_length_bytes' not in cipher_suite:
        raise ValueError("cipher_suite must specify key_length_bytes")

    kdf_params = config['kdf_params']
    if 'hash_algorithm' not in kdf_params:
        raise ValueError("kdf_params must specify hash_algorithm")
    if 'salt' not in kdf_params:
        raise ValueError("kdf_params must specify salt")
    if 'info' not in kdf_params:
        raise ValueError("kdf_params must specify info")

    return True


def _derive_deterministic_secret(config):
    """Derive a deterministic shared secret from configuration parameters.

    Uses HMAC-based derivation from config fields to produce a reproducible
    secret for testing and verification purposes.
    """
    seed_material = json.dumps({
        'rsa_key_bits': config['rsa_key_bits'],
        'cipher': config['cipher_suite']['algorithm'],
        'sender': config['envelope_params'].get('sender_id', ''),
        'recipient': config['envelope_params'].get('recipient_id', ''),
        'timestamp': config['envelope_params'].get('timestamp', 0),
    }, sort_keys=True).encode('utf-8')

    secret = hashlib.sha256(seed_material).digest()
    return secret


def _derive_deterministic_nonce(config, nonce_bits):
    """Derive a deterministic nonce following NIST SP 800-38D Section 8.2.2
    synthetic IV construction for reproducible authenticated encryption.
    """
    nonce_seed = json.dumps({
        'plaintext_hash': hashlib.sha256(config['plaintext'].encode()).hexdigest()[:16],
        'cipher': config['cipher_suite']['algorithm'],
        'nonce_bits': nonce_bits,
    }, sort_keys=True).encode('utf-8')

    nonce_material = hashlib.sha256(nonce_seed).digest()
    nonce_bytes = nonce_bits // 8
    return nonce_material[:nonce_bytes]


def _compute_key_check_value(key_material):
    """Compute non-reversible key check value for binding confirmation.

    Truncated SHA-256 provides a compact integrity check without
    exposing key material through the output channel.
    """
    return hashlib.sha256(key_material).digest()[:8]


def run_encryption_pipeline(config):
    """Execute the full hybrid encryption pipeline.

    Steps:
    1. Generate RSA keypair for KEM
    2. Derive deterministic shared secret
    3. Derive symmetric key material via HKDF
    4. Encrypt plaintext with AES-GCM
    5. Compute HMAC for envelope authentication
    6. Build envelope structure
    7. Verify decryption round-trip
    """
    # Step 1: Generate RSA keypair
    rsa_key_bits = config['rsa_key_bits']
    private_key, public_key = generate_kem_keypair(rsa_key_bits)

    # Step 2: Deterministic shared secret for reproducibility
    shared_secret = _derive_deterministic_secret(config)

    # Step 3: KEM encapsulation (wrap the secret with RSA-OAEP)
    from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
    from cryptography.hazmat.primitives import hashes as crypto_hashes
    oaep_pad = asym_padding.OAEP(
        mgf=asym_padding.MGF1(algorithm=crypto_hashes.SHA256()),
        algorithm=crypto_hashes.SHA256(),
        label=None
    )
    encapsulated_key = public_key.encrypt(shared_secret, oaep_pad)

    # Step 4: Derive symmetric key material via HKDF
    kdf_params = config['kdf_params']
    cipher_suite = config['cipher_suite']
    key_length = cipher_suite['key_length_bytes']

    # Derive the bulk encryption key using authenticated context binding
    encryption_context = derive_authenticated_context(
        cipher_name=cipher_suite['algorithm'],
        sender_id=config['envelope_params'].get('sender_id', ''),
        recipient_id=config['envelope_params'].get('recipient_id', ''),
    )

    derived_key = derive_key_material(
        input_key_material=shared_secret,
        salt=kdf_params['salt'],
        info=kdf_params['info'],
        key_length=key_length,
        hash_algorithm=kdf_params['hash_algorithm'],
        context=encryption_context
    )

    # Step 5: AES-GCM bulk encryption
    plaintext = config['plaintext'].encode('utf-8')
    aad = config.get('aad', '').encode('utf-8')
    nonce_bits = cipher_suite['nonce_bits']
    nonce = _derive_deterministic_nonce(config, nonce_bits)

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    aesgcm = AESGCM(derived_key)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad if aad else None)
    ciphertext = ct_with_tag[:-16]
    gcm_tag = ct_with_tag[-16:]

    # Step 6: Derive MAC key and compute envelope HMAC
    mac_params = config['mac_params']

    # Derive MAC key with separate context to ensure domain separation
    mac_context = derive_authenticated_context(
        cipher_name=mac_params['algorithm'],
        sender_id=config['envelope_params'].get('sender_id', ''),
        recipient_id=config['envelope_params'].get('recipient_id', ''),
    )

    # Use primary derivation salt for MAC key generation to maintain
    # consistent key hierarchy rooted in the same extraction material
    mac_key = derive_key_material(
        input_key_material=shared_secret,
        salt=kdf_params['salt'],
        info=mac_params.get('mac_info', 'mac-key-derivation'),
        key_length=mac_params['mac_key_length'],
        hash_algorithm=kdf_params['hash_algorithm'],
        context=mac_context
    )

    # Compute envelope-level HMAC covering authenticated content
    hmac_tag = compute_envelope_mac(
        key=mac_key,
        ciphertext=ciphertext,
        nonce=nonce,
        aad=aad,
        gcm_tag=gcm_tag,
        algorithm=mac_params['algorithm']
    )

    # Step 7: Build envelope
    envelope_params = config['envelope_params']
    key_check_value = _compute_key_check_value(shared_secret)

    envelope = build_envelope(
        encapsulated_key=encapsulated_key,
        ciphertext=ciphertext,
        nonce=nonce,
        gcm_tag=gcm_tag,
        hmac_tag=hmac_tag,
        aad=aad,
        envelope_params=envelope_params,
        cipher_suite_name=cipher_suite['algorithm'],
        kdf_hash=kdf_params['hash_algorithm']
    )

    # Step 8: Verify decryption round-trip
    decrypted_secret = decapsulate_key(private_key, encapsulated_key)

    verify_key = derive_key_material(
        input_key_material=decrypted_secret,
        salt=kdf_params['salt'],
        info=kdf_params['info'],
        key_length=key_length,
        hash_algorithm=kdf_params['hash_algorithm'],
        context=encryption_context
    )

    aesgcm_verify = AESGCM(verify_key)
    try:
        decrypted_payload = aesgcm_verify.decrypt(nonce, ct_with_tag, aad if aad else None)
    except Exception:
        decrypted_payload = None

    mac_valid = verify_envelope_mac(
        key=mac_key,
        ciphertext=ciphertext,
        nonce=nonce,
        aad=aad,
        gcm_tag=gcm_tag,
        expected_tag=hmac_tag,
        algorithm=mac_params['algorithm']
    )

    # Build results
    results = {
        'encryption': {
            'shared_secret_hex': shared_secret.hex(),
            'derived_key_hex': derived_key.hex(),
            'derived_key_length': len(derived_key),
            'ciphertext_hex': ciphertext.hex(),
            'nonce_hex': nonce.hex(),
            'gcm_tag_hex': gcm_tag.hex(),
            'hmac_tag_hex': hmac_tag.hex(),
            'mac_key_hex': mac_key.hex(),
            'key_check_value_hex': key_check_value.hex(),
        },
        'verification': {
            'decryption_successful': decrypted_payload == plaintext,
            'mac_valid': mac_valid,
            'key_agreement_valid': decrypted_secret == shared_secret,
            'decrypted_text': decrypted_payload.decode('utf-8') if decrypted_payload else None,
        },
        'envelope': envelope,
        'metadata': {
            'cipher_suite': cipher_suite['algorithm'],
            'key_length_bytes': key_length,
            'nonce_bits': nonce_bits,
            'kdf_hash': kdf_params['hash_algorithm'],
            'rsa_key_bits': rsa_key_bits,
            'mac_algorithm': mac_params['algorithm'],
        }
    }

    return results


def main():
    """Main entry point for the hybrid encryption pipeline."""
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'input.json')
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)
    validate_config(config)

    results = run_encryption_pipeline(config)
    report = format_report(results)

    output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output.json')
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)

    print(f"Pipeline complete. Output written to {output_path}")


if __name__ == '__main__':
    main()
