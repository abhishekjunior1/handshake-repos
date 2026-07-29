"""
Envelope builder module that assembles encrypted payloads, headers,
and MAC tags into a structured cryptographic envelope format.

Envelope format:
    [version: 1 byte][flags: 1 byte][header_len: 2 bytes][header: variable]
    [payload_len: 4 bytes][encrypted_payload: variable]
    [mac_tag: 32 bytes]
"""

import struct
import json
import hashlib


# Envelope version
ENVELOPE_VERSION = 0x02

# Flag bits
FLAG_COMPRESSED = 0x01
FLAG_AUTHENTICATED = 0x02
FLAG_ENCRYPTED = 0x04
FLAG_HAS_METADATA = 0x08


def build_header(sender_id: str, recipient_id: str,
                 nonce: bytes, metadata: dict = None) -> bytes:
    """
    Build the envelope header containing routing and crypto parameters.

    Parameters:
        sender_id: Identifier of the message sender
        recipient_id: Identifier of the intended recipient
        nonce: Cryptographic nonce used for encryption
        metadata: Optional additional metadata dictionary

    Returns:
        Serialized header bytes
    """
    header_data = {
        "sender": sender_id,
        "recipient": recipient_id,
        "nonce_hex": nonce.hex(),
        "nonce_length": len(nonce),
    }

    if metadata:
        header_data["metadata"] = metadata

    # Serialize as compact JSON (deterministic key ordering)
    header_json = json.dumps(header_data, sort_keys=True,
                            separators=(',', ':')).encode('utf-8')
    return header_json


def build_envelope(header: bytes, encrypted_payload: bytes,
                   mac_tag: bytes, flags: int = None) -> bytes:
    """
    Assemble the complete envelope from components.

    Parameters:
        header: Serialized header bytes
        encrypted_payload: Encrypted message payload
        mac_tag: Authentication tag
        flags: Envelope flags (auto-detected if None)

    Returns:
        Complete serialized envelope
    """
    if flags is None:
        flags = FLAG_AUTHENTICATED | FLAG_ENCRYPTED

    if len(header) > 65535:
        raise ValueError("Header too large (max 65535 bytes)")
    if len(encrypted_payload) > 2**32 - 1:
        raise ValueError("Payload too large")

    envelope = bytearray()

    # Version byte
    envelope.append(ENVELOPE_VERSION)

    # Flags byte
    envelope.append(flags & 0xFF)

    # Header length (2 bytes, big-endian) + header
    envelope.extend(struct.pack('>H', len(header)))
    envelope.extend(header)

    # Payload length (4 bytes, big-endian) + encrypted payload
    envelope.extend(struct.pack('>I', len(encrypted_payload)))
    envelope.extend(encrypted_payload)

    # MAC tag (fixed 32 bytes)
    if len(mac_tag) != 32:
        raise ValueError("MAC tag must be 32 bytes")
    envelope.extend(mac_tag)

    return bytes(envelope)


def parse_envelope(envelope: bytes) -> dict:
    """
    Parse a serialized envelope into its components.

    Parameters:
        envelope: Complete serialized envelope bytes

    Returns:
        Dictionary with keys: version, flags, header, payload, mac_tag
    """
    if len(envelope) < 40:  # minimum: 1+1+2+0+4+0+32
        raise ValueError("Envelope too short")

    offset = 0

    # Version
    version = envelope[offset]
    offset += 1

    # Flags
    flags = envelope[offset]
    offset += 1

    # Header
    header_len = struct.unpack('>H', envelope[offset:offset+2])[0]
    offset += 2
    header = envelope[offset:offset+header_len]
    offset += header_len

    # Payload
    payload_len = struct.unpack('>I', envelope[offset:offset+4])[0]
    offset += 4
    payload = envelope[offset:offset+payload_len]
    offset += payload_len

    # MAC tag
    mac_tag = envelope[offset:offset+32]

    return {
        "version": version,
        "flags": flags,
        "header": header,
        "header_parsed": json.loads(header.decode('utf-8')),
        "payload": payload,
        "mac_tag": mac_tag,
        "total_size": len(envelope),
    }


def compute_envelope_digest(envelope: bytes) -> str:
    """
    Compute a hex digest of the entire envelope for logging.
    """
    return hashlib.sha256(envelope).hexdigest()


def build_multi_recipient_envelope(header: bytes, encrypted_payload: bytes,
                                    mac_tag: bytes, recipient_keys: list) -> bytes:
    """
    Build an envelope with multiple recipient key slots.

    Each recipient gets a wrapped copy of the session key, allowing
    any of them to decrypt the payload. The payload itself is encrypted
    once with a single session key.

    Parameters:
        header: Serialized header
        encrypted_payload: Encrypted payload (encrypted with session key)
        mac_tag: Authentication tag
        recipient_keys: List of wrapped session key bytes (one per recipient)

    Returns:
        Multi-recipient envelope bytes
    """
    flags = FLAG_AUTHENTICATED | FLAG_ENCRYPTED | FLAG_HAS_METADATA

    envelope = bytearray()
    envelope.append(ENVELOPE_VERSION)
    envelope.append(flags & 0xFF)

    # Header
    envelope.extend(struct.pack('>H', len(header)))
    envelope.extend(header)

    # Recipient count and wrapped keys
    envelope.extend(struct.pack('>H', len(recipient_keys)))
    for wrapped_key in recipient_keys:
        envelope.extend(struct.pack('>H', len(wrapped_key)))
        envelope.extend(wrapped_key)

    # Payload
    envelope.extend(struct.pack('>I', len(encrypted_payload)))
    envelope.extend(encrypted_payload)

    # MAC
    envelope.extend(mac_tag)

    return bytes(envelope)


def validate_envelope_structure(envelope: bytes) -> dict:
    """
    Validate envelope structure without verifying cryptographic properties.

    Returns validation result with any structural issues found.
    """
    result = {"valid": True, "issues": [], "size": len(envelope)}

    try:
        parsed = parse_envelope(envelope)
        result["version"] = parsed["version"]
        result["flags"] = parsed["flags"]
        result["header_size"] = len(parsed["header"])
        result["payload_size"] = len(parsed["payload"])

        if parsed["version"] != ENVELOPE_VERSION:
            result["issues"].append(f"Unknown version: {parsed['version']}")
            result["valid"] = False

    except (ValueError, struct.error, json.JSONDecodeError) as e:
        result["valid"] = False
        result["issues"].append(str(e))

    return result
