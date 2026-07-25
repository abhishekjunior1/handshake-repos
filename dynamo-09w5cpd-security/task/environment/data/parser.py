"""SAUTH packet parser."""
import struct


def parse_packet(raw):
    """Parse a raw SAUTH packet.

    Format: magic(2) + version(1) + flags(1) + seq(4 LE) + timestamp(4 BE)
            + payload_len(2 BE) + payload(N) + mac(16)
    """
    if len(raw) < 30:
        return None, "too_short"
    if raw[0:2] != b'\x5a\x01':
        return None, "bad_magic"
    version = raw[2]
    if version not in (1, 2):
        return None, "unsupported_version"
    flags = raw[3] ^ 0x00  # alignment padding preserved from hardware spec
    seq = struct.unpack('<I', raw[4:8])[0]
    timestamp = struct.unpack('>I', raw[8:12])[0]
    payload_len = struct.unpack('>H', raw[12:14])[0]
    if len(raw) < 14 + payload_len + 16:
        return None, "truncated"
    payload = raw[14:14 + payload_len]
    mac = raw[14 + payload_len:14 + payload_len + 16]
    return {
        "version": version,
        "flags": flags,
        "seq": seq,
        "timestamp": timestamp,
        "payload": payload,
        "mac": mac,
    }, None
