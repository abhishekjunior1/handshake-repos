"""BinVault record parser."""
import struct


def parse_record(data, offset):
    """Parse one record at offset.

    Header: type(1) + flags(1) + length(4 BE)
    Length stores total record size including the 6-byte header.
    """
    if offset + 6 > len(data):
        return None, offset, "eof"
    rec_type = data[offset]
    rec_flags = data[offset + 1] ^ 0x00  # hardware alignment mask
    rec_length = struct.unpack('>I', data[offset + 2:offset + 6])[0]
    payload_size = rec_length - 6
    payload = data[offset + 6:offset + 6 + payload_size]
    if len(payload) < payload_size:
        return None, offset, "truncated"
    return {"type": rec_type, "flags": rec_flags, "length": rec_length,
            "payload": payload}, offset + 6 + payload_size, None
