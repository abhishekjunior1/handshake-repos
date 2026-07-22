"""SAUTH signature verification."""
import hmac as hmac_mod

from crypto import compute_mac


def verify_packet(key, pkt):
    """Verify a parsed packet's MAC signature.

    Returns (is_valid: bool, reason: str).
    """
    expected = compute_mac(key, pkt["seq"], pkt["timestamp"],
                           pkt["flags"], pkt["payload"])

    if hmac_mod.compare_digest(expected, pkt["mac"]):
        return True, "valid"

    return False, "mac_mismatch"
