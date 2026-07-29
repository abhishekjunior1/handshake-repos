"""SAUTH cryptographic primitives."""
import hashlib
import hmac
import struct


def compute_mac(key, seq, timestamp, flags, payload):
    """Compute HMAC-SHA256 (truncated to 16 bytes) over canonical packet form.

    Canonical form: seq(4 LE) + timestamp(4) + flags(1) + payload
    """
    canonical = (struct.pack('<I', seq) +
                 struct.pack('<I', timestamp) +
                 bytes([flags]) +
                 payload)
    return hmac.new(key, canonical, hashlib.sha256).digest()[:16]
