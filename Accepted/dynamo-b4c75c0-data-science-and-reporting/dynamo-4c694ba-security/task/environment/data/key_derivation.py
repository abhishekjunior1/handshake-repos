"""
Key derivation module implementing a custom HKDF-inspired key derivation function.

Uses iterative extraction and expansion phases to derive cryptographic keys
from a master secret, salt, and context information string.
"""

import hashlib
import struct


def _hmac_sha256(key: bytes, data: bytes) -> bytes:
    """Compute HMAC-SHA256 using the given key and data."""
    block_size = 64
    if len(key) > block_size:
        key = hashlib.sha256(key).digest()
    key = key.ljust(block_size, b'\x00')

    o_key_pad = bytes(b ^ 0x5C for b in key)
    i_key_pad = bytes(b ^ 0x36 for b in key)

    inner_hash = hashlib.sha256(i_key_pad + data).digest()
    return hashlib.sha256(o_key_pad + inner_hash).digest()


def _extract(salt: bytes, input_key_material: bytes) -> bytes:
    """
    Extract phase: compress input key material into a fixed-length
    pseudorandom key using the salt as HMAC key.
    """
    return _hmac_sha256(salt, input_key_material)


def _expand(prk: bytes, info: bytes, length: int, iterations: int) -> bytes:
    """
    Expand phase: expand the pseudorandom key into output key material
    of the specified length, using the info string for domain separation.

    The iterations parameter controls the number of strengthening rounds
    applied during expansion to increase computational cost.
    """
    output = b''
    previous_block = b''
    block_number = 1

    while len(output) < length:
        # Each block depends on the previous block, info, and counter
        data = previous_block + info + struct.pack('>I', block_number)

        # Apply strengthening iterations
        current = _hmac_sha256(prk, data)
        for _ in range(iterations - 1):
            current = _hmac_sha256(prk, current + data)

        previous_block = current
        output += current
        block_number += 1

    return output[:length]


def derive_key(master_secret: bytes, salt: bytes, info: bytes,
               key_length: int, iterations: int = 1) -> bytes:
    """
    Derive a cryptographic key from the master secret.

    Parameters:
        master_secret: The input key material (shared secret)
        salt: Random salt value for extraction
        info: Context/application-specific information for domain separation
        key_length: Desired output key length in bytes
        iterations: Number of strengthening iterations (minimum 1)

    Returns:
        Derived key of the specified length
    """
    if key_length <= 0:
        raise ValueError("Key length must be positive")
    if iterations < 1:
        raise ValueError("Iterations must be at least 1")
    if len(master_secret) == 0:
        raise ValueError("Master secret cannot be empty")

    # Maximum output is 255 * hash_length (SHA-256 = 32 bytes)
    max_length = 255 * 32
    if key_length > max_length:
        raise ValueError(f"Key length exceeds maximum ({max_length} bytes)")

    # Extract phase
    prk = _extract(salt, master_secret)

    # Expand phase with domain separation via info string
    derived = _expand(prk, info, key_length, iterations)

    return derived


def derive_key_pair(master_secret: bytes, salt: bytes,
                    enc_info: bytes, mac_info: bytes,
                    key_length: int, iterations: int = 1) -> tuple:
    """
    Derive a pair of keys (encryption + MAC) from the same master secret,
    using different info strings for cryptographic domain separation.

    Parameters:
        master_secret: The input key material
        salt: Random salt value
        enc_info: Info string for encryption key derivation
        mac_info: Info string for MAC key derivation
        key_length: Length of each key in bytes
        iterations: Strengthening iterations

    Returns:
        Tuple of (encryption_key, mac_key)
    """
    enc_key = derive_key(master_secret, salt, enc_info, key_length, iterations)
    mac_key = derive_key(master_secret, salt, mac_info, key_length, iterations)
    return enc_key, mac_key


def compute_key_fingerprint(key: bytes) -> str:
    """
    Compute a short fingerprint of a key for logging/debugging.
    Returns first 8 hex characters of SHA-256 hash.
    """
    return hashlib.sha256(key).hexdigest()[:8]


def validate_key_material(master_secret: bytes, salt: bytes) -> dict:
    """
    Validate input key material and return diagnostic information.

    Returns a dict with validation results and entropy estimates.
    """
    result = {
        "master_secret_length": len(master_secret),
        "salt_length": len(salt),
        "valid": True,
        "warnings": []
    }

    if len(master_secret) < 16:
        result["warnings"].append("Master secret shorter than 128 bits")
    if len(salt) < 16:
        result["warnings"].append("Salt shorter than 128 bits")
    if master_secret == b'\x00' * len(master_secret):
        result["warnings"].append("Master secret is all zeros")
    if salt == b'\x00' * len(salt):
        result["warnings"].append("Salt is all zeros")

    # Estimate byte entropy using simple compression heuristic
    unique_bytes = len(set(master_secret))
    result["estimated_entropy_bits"] = unique_bytes * 8

    return result
