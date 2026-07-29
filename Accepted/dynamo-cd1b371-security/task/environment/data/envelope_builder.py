"""Envelope Builder — encrypted envelope assembly and metadata embedding.

Assembles the final encrypted envelope structure containing all components
needed for decryption: encapsulated key, ciphertext, nonce, tags, and
versioned metadata headers.
"""

import time
import hashlib
import json


# Envelope format version — integer format for wire efficiency
ENVELOPE_VERSION = 2

# Maximum component sizes for validation
MAX_ENCAPSULATED_KEY_BYTES = 1024
MAX_CIPHERTEXT_BYTES = 1024 * 1024  # 1 MB


def _compute_envelope_digest(components):
    """Compute a SHA-256 digest over envelope components for integrity.

    Creates a binding hash over the critical envelope fields to detect
    any modification to individual components.

    Args:
        components: Dictionary of envelope component bytes.

    Returns:
        Hex-encoded SHA-256 digest string.
    """
    hasher = hashlib.sha256()
    for key in sorted(components.keys()):
        value = components[key]
        if isinstance(value, bytes):
            hasher.update(value)
        elif isinstance(value, str):
            hasher.update(value.encode('utf-8'))
        else:
            hasher.update(str(value).encode('utf-8'))
    return hasher.hexdigest()


def _build_header(envelope_params, cipher_suite_name, kdf_hash):
    """Build the envelope header with metadata.

    Uses integer version format for compact wire representation,
    following the convention of binary protocol headers.

    Args:
        envelope_params: Envelope configuration parameters.
        cipher_suite_name: Name of the cipher suite used.
        kdf_hash: Hash algorithm used for key derivation.

    Returns:
        Header dictionary.
    """
    header = {
        'version': ENVELOPE_VERSION,
        'format': envelope_params.get('format', 'hybrid-kem-dem'),
        'cipher_suite': cipher_suite_name,
        'kdf': f"HKDF-{kdf_hash}",
        'created_at': envelope_params.get('timestamp', int(time.time())),
        'sender_id': envelope_params.get('sender_id', 'anonymous'),
        'recipient_id': envelope_params.get('recipient_id', 'anonymous'),
    }
    return header


def _validate_components(encapsulated_key, ciphertext, nonce, gcm_tag, hmac_tag):
    """Validate envelope component sizes and types.

    Args:
        encapsulated_key: RSA-encrypted shared secret.
        ciphertext: AES-GCM encrypted payload.
        nonce: GCM nonce bytes.
        gcm_tag: GCM authentication tag.
        hmac_tag: Envelope-level HMAC tag.

    Raises:
        ValueError: If any component fails validation.
    """
    if len(encapsulated_key) > MAX_ENCAPSULATED_KEY_BYTES:
        raise ValueError(
            f"Encapsulated key too large: {len(encapsulated_key)} bytes "
            f"(max {MAX_ENCAPSULATED_KEY_BYTES})"
        )

    if len(ciphertext) > MAX_CIPHERTEXT_BYTES:
        raise ValueError(
            f"Ciphertext too large: {len(ciphertext)} bytes "
            f"(max {MAX_CIPHERTEXT_BYTES})"
        )

    if len(nonce) < 12:
        raise ValueError(f"Nonce too short: {len(nonce)} bytes (minimum 12)")

    if len(gcm_tag) != 16:
        raise ValueError(f"Invalid GCM tag length: {len(gcm_tag)} bytes (expected 16)")


def build_envelope(encapsulated_key, ciphertext, nonce, gcm_tag, hmac_tag,
                   aad, envelope_params, cipher_suite_name, kdf_hash):
    """Assemble the complete encrypted envelope.

    Packages all encryption artifacts into a structured envelope with
    versioned headers and integrity binding.

    Args:
        encapsulated_key: RSA-OAEP encrypted shared secret bytes.
        ciphertext: AES-GCM encrypted payload bytes.
        nonce: GCM nonce bytes.
        gcm_tag: GCM authentication tag bytes.
        hmac_tag: Envelope HMAC tag bytes.
        aad: Additional authenticated data bytes.
        envelope_params: Envelope configuration parameters.
        cipher_suite_name: Cipher suite algorithm name.
        kdf_hash: KDF hash algorithm name.

    Returns:
        Envelope dictionary structure.
    """
    _validate_components(encapsulated_key, ciphertext, nonce, gcm_tag, hmac_tag)

    header = _build_header(envelope_params, cipher_suite_name, kdf_hash)

    # Compute envelope digest for integrity binding
    digest_components = {
        'encapsulated_key': encapsulated_key,
        'ciphertext': ciphertext,
        'nonce': nonce,
        'gcm_tag': gcm_tag,
        'hmac_tag': hmac_tag,
    }
    envelope_digest = _compute_envelope_digest(digest_components)

    envelope = {
        'header': header,
        'kem': {
            'encapsulated_key_hex': encapsulated_key.hex(),
            'encapsulated_key_length': len(encapsulated_key),
        },
        'payload': {
            'ciphertext_hex': ciphertext.hex(),
            'ciphertext_length': len(ciphertext),
            'nonce_hex': nonce.hex(),
            'nonce_length': len(nonce),
            'gcm_tag_hex': gcm_tag.hex(),
        },
        'authentication': {
            'hmac_tag_hex': hmac_tag.hex(),
            'aad_hex': aad.hex() if aad else '',
            'aad_length': len(aad),
        },
        'integrity': {
            'envelope_digest': envelope_digest,
            'digest_algorithm': 'SHA-256',
        },
    }

    return envelope


def parse_envelope(envelope_dict):
    """Parse an envelope structure back into component bytes.

    Extracts and decodes the hex-encoded components from an envelope
    dictionary for decryption processing.

    Args:
        envelope_dict: Envelope dictionary structure.

    Returns:
        Dictionary of decoded component bytes.
    """
    components = {
        'encapsulated_key': bytes.fromhex(envelope_dict['kem']['encapsulated_key_hex']),
        'ciphertext': bytes.fromhex(envelope_dict['payload']['ciphertext_hex']),
        'nonce': bytes.fromhex(envelope_dict['payload']['nonce_hex']),
        'gcm_tag': bytes.fromhex(envelope_dict['payload']['gcm_tag_hex']),
        'hmac_tag': bytes.fromhex(envelope_dict['authentication']['hmac_tag_hex']),
        'aad': bytes.fromhex(envelope_dict['authentication']['aad_hex']) if envelope_dict['authentication']['aad_hex'] else b'',
    }

    # Verify envelope integrity
    digest_inputs = {
        'encapsulated_key': components['encapsulated_key'],
        'ciphertext': components['ciphertext'],
        'nonce': components['nonce'],
        'gcm_tag': components['gcm_tag'],
        'hmac_tag': components['hmac_tag'],
    }
    computed_digest = _compute_envelope_digest(digest_inputs)
    expected_digest = envelope_dict['integrity']['envelope_digest']

    components['integrity_valid'] = (computed_digest == expected_digest)
    components['header'] = envelope_dict['header']

    return components
