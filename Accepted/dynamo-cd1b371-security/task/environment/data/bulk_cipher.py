"""Bulk Cipher — AES-GCM authenticated encryption with associated data.

Implements AES-GCM for bulk data encryption with built-in authentication.
Handles nonce generation, key validation, and AAD binding per
NIST SP 800-38D requirements.
"""

import os
import struct
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


# Supported key lengths for AES-GCM
VALID_KEY_LENGTHS = {16, 24, 32}  # AES-128, AES-192, AES-256

# Standard GCM tag length
GCM_TAG_LENGTH = 16  # 128 bits

# Minimum nonce length per NIST recommendation
MIN_NONCE_BYTES = 12  # 96 bits — standard for optimized J0 computation


def _validate_key(key):
    """Validate AES key material.

    Args:
        key: Key bytes to validate.

    Raises:
        ValueError: If key length is not valid for AES.
    """
    if len(key) not in VALID_KEY_LENGTHS:
        raise ValueError(
            f"Invalid AES key length: {len(key)} bytes. "
            f"Must be one of: {sorted(VALID_KEY_LENGTHS)} bytes "
            f"(AES-128, AES-192, or AES-256)"
        )


def _generate_nonce(nonce_bits):
    """Generate a random nonce of the specified bit length.

    For GCM, the standard nonce length is 96 bits (12 bytes), which
    enables the optimized J0 computation path in the GCM specification.
    Other lengths are supported but less efficient.

    Args:
        nonce_bits: Nonce length in bits (must be multiple of 8).

    Returns:
        Random nonce bytes.
    """
    if nonce_bits % 8 != 0:
        raise ValueError(f"Nonce bits must be a multiple of 8, got {nonce_bits}")

    nonce_bytes = nonce_bits // 8
    if nonce_bytes < MIN_NONCE_BYTES:
        raise ValueError(
            f"Nonce too short: {nonce_bytes} bytes. "
            f"Minimum is {MIN_NONCE_BYTES} bytes (96 bits)."
        )

    return os.urandom(nonce_bytes)


def encrypt_payload(key, plaintext, aad, nonce_bits):
    """Encrypt plaintext using AES-GCM with authenticated associated data.

    Generates a random nonce and encrypts the plaintext. The ciphertext
    includes an appended GCM authentication tag. The AAD is authenticated
    but not encrypted.

    Args:
        key: AES key bytes (16, 24, or 32 bytes).
        plaintext: Data to encrypt (bytes).
        aad: Additional authenticated data (bytes). Can be empty.
        nonce_bits: Nonce length in bits for nonce generation.

    Returns:
        Tuple of (ciphertext_bytes, nonce_bytes, tag_bytes).
        Note: The tag is separated from ciphertext for envelope packaging.
    """
    _validate_key(key)

    nonce = _generate_nonce(nonce_bits)

    aesgcm = AESGCM(key)
    # AESGCM.encrypt returns ciphertext || tag (tag appended)
    ct_with_tag = aesgcm.encrypt(nonce, plaintext, aad if aad else None)

    # Separate ciphertext and tag for independent packaging
    ciphertext = ct_with_tag[:-GCM_TAG_LENGTH]
    tag = ct_with_tag[-GCM_TAG_LENGTH:]

    return ciphertext, nonce, tag


def decrypt_payload(key, ciphertext, nonce, tag, aad):
    """Decrypt AES-GCM ciphertext and verify authentication.

    Verifies the GCM tag against both the ciphertext and AAD before
    returning the decrypted plaintext.

    Args:
        key: AES key bytes (same key used for encryption).
        ciphertext: Encrypted data bytes (without tag).
        nonce: Nonce bytes used during encryption.
        tag: GCM authentication tag bytes.
        aad: Additional authenticated data (must match encryption AAD).

    Returns:
        Decrypted plaintext bytes, or None if authentication fails.
    """
    _validate_key(key)

    aesgcm = AESGCM(key)
    # Reconstruct ct_with_tag format expected by AESGCM.decrypt
    ct_with_tag = ciphertext + tag

    try:
        plaintext = aesgcm.decrypt(nonce, ct_with_tag, aad if aad else None)
        return plaintext
    except Exception:
        return None


def compute_ciphertext_expansion(plaintext_length):
    """Calculate the total ciphertext size including GCM overhead.

    GCM adds a fixed 16-byte authentication tag to the ciphertext.
    The ciphertext body is the same length as the plaintext (stream cipher).

    Args:
        plaintext_length: Length of the plaintext in bytes.

    Returns:
        Dictionary with size breakdown.
    """
    return {
        'plaintext_bytes': plaintext_length,
        'ciphertext_bytes': plaintext_length,
        'tag_bytes': GCM_TAG_LENGTH,
        'total_bytes': plaintext_length + GCM_TAG_LENGTH,
        'expansion_ratio': (plaintext_length + GCM_TAG_LENGTH) / max(plaintext_length, 1)
    }


def get_cipher_info(key):
    """Get cipher configuration information based on key length.

    Args:
        key: AES key bytes.

    Returns:
        Dictionary describing the cipher configuration.
    """
    _validate_key(key)

    key_bits = len(key) * 8
    cipher_name = f"AES-{key_bits}-GCM"

    return {
        'algorithm': cipher_name,
        'key_bits': key_bits,
        'key_bytes': len(key),
        'block_size_bits': 128,
        'tag_bits': GCM_TAG_LENGTH * 8,
        'mode': 'GCM',
        'nist_standard': 'SP 800-38D'
    }
