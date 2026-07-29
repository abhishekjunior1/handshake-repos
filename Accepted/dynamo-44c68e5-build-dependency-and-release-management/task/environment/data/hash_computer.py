"""Nix-compatible hash computation utilities for derivation store paths."""

import hashlib

NIX_BASE32_CHARS = '0123456789abcdfghijklmnpqrsvwxyz'
SELF_REF_PLACEHOLDER = '/nix/store/ffffffffffffffffffffffffffffffff'


def nix_base32_encode(data: bytes) -> str:
    """Encode bytes using Nix-specific base32 alphabet."""
    if not data:
        return ''
    hash_len = len(data)
    encoded_len = (hash_len * 8 + 4) // 5
    result = []
    for n in range(encoded_len - 1, -1, -1):
        b = n * 5
        byte_idx = b // 8
        bit_idx = b % 8
        c = (data[byte_idx] >> bit_idx) & 0x1f
        if bit_idx > 3 and byte_idx + 1 < hash_len:
            c |= (data[byte_idx + 1] << (8 - bit_idx)) & 0x1f
        result.append(NIX_BASE32_CHARS[c])
    return ''.join(result)


def compress_hash(hex_hash: str, target_bytes=20) -> bytes:
    """XOR-fold a hex hash down to target_bytes via cyclic compression."""
    full_bytes = bytes.fromhex(hex_hash)
    result = bytearray(target_bytes)
    for i, b in enumerate(full_bytes):
        result[i % target_bytes] ^= b
    return bytes(result)


def hash_string(s: str) -> str:
    """Compute SHA-256 hex digest of a UTF-8 string."""
    return hashlib.sha256(s.encode('utf-8')).hexdigest()


def hash_derivation_inputs(drv, input_paths) -> str:
    """Hash derivation inputs including all input store paths for input-addressed derivations."""
    fingerprint_parts = [
        'output:out',
        drv.get('hash_algo', 'sha256'),
        drv['name'],
        drv.get('builder', '/bin/bash'),
    ]
    fingerprint_parts.extend(sorted(input_paths))
    fingerprint_parts.extend(drv.get('build_args', []))
    fingerprint = ':'.join(fingerprint_parts)
    return hash_string(fingerprint)


def hash_derivation_modulo(drv) -> str:
    """Hash a fixed-output derivation using only its declared output hash."""
    fingerprint = ':'.join([
        'fixed:out',
        drv.get('hash_algo', 'sha256'),
        drv.get('output_hash', ''),
        drv['name'],
    ])
    return hash_string(fingerprint)


def compute_content_hash(data: bytes) -> str:
    """Compute SHA-256 hex digest of raw byte content."""
    return hashlib.sha256(data).hexdigest()


def hash_path(path_str):
    """Hash a store path string for lookup purposes."""
    return hashlib.sha256(path_str.encode()).hexdigest()[:40]


def validate_store_path_format(path):
    """Check if a path follows /nix/store/<32-char-hash>-<name> format."""
    import re
    pattern = r'^/nix/store/[0-9a-z]{32}-.+$'
    return bool(re.match(pattern, path))
