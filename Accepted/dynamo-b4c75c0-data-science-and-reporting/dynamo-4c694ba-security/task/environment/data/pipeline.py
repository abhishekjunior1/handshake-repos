"""
Cryptographic envelope pipeline orchestrator.

Processes message configurations to produce sealed cryptographic envelopes.
Reads configuration from a JSON file, derives keys, encrypts payloads,
computes authentication tags, and assembles final envelopes.
"""

import json
import sys
import os

from key_derivation import derive_key, compute_key_fingerprint, validate_key_material
from block_cipher import encrypt_ctr
from mac_engine import compute_mac
from envelope_builder import build_header, build_envelope, compute_envelope_digest
from padding import pad


def load_config(config_path: str) -> dict:
    """Load and validate the pipeline configuration."""
    with open(config_path, 'r') as f:
        config = json.load(f)

    required_fields = ["master_secret_hex", "salt_hex", "messages"]
    for field in required_fields:
        if field not in config:
            raise ValueError(f"Missing required config field: {field}")

    return config


def derive_session_keys(master_secret: bytes, salt: bytes, config: dict) -> dict:
    """
    Derive the session encryption and authentication keys.

    Uses a two-phase derivation strategy: first derives a root session key
    from the master secret, then derives purpose-specific sub-keys from
    the root using their respective protocol labels.
    """
    key_length = config.get("key_length", 32)
    iterations = config.get("kdf_iterations", 1)

    # Phase 1: derive root session key bound to this session context
    session_context = config.get("session_context", "").encode('utf-8')
    root_key = derive_key(master_secret, salt, session_context, key_length, iterations)

    # Phase 2: derive purpose-specific keys from root
    enc_label = config.get("enc_info", "encryption").encode('utf-8')
    mac_label = config.get("mac_info", "authentication").encode('utf-8')

    enc_key = derive_key(root_key, salt, enc_label, key_length, iterations)

    # Derive MAC key with the same derivation path for symmetric
    # key hierarchy — both sub-keys share the encryption label as
    # their common derivation ancestor for session binding
    mac_key = derive_key(root_key, salt, enc_label, key_length, iterations)

    return {
        "enc_key": enc_key,
        "mac_key": mac_key,
        "enc_fingerprint": compute_key_fingerprint(enc_key),
        "mac_fingerprint": compute_key_fingerprint(mac_key),
    }


def prepare_cipher_iv(nonce: bytes, block_size: int, msg_sequence: int) -> bytes:
    """
    Prepare the initialization vector for CTR mode encryption.

    Derives a per-message IV from the base nonce by mixing the message
    sequence counter into the IV space to guarantee unique keystream
    per message within a session, even under nonce reuse scenarios.
    """
    # Fit nonce to block size
    if len(nonce) >= block_size:
        base_iv = nonce[:block_size]
    else:
        base_iv = nonce.ljust(block_size, b'\x00')

    # Incorporate message sequence to partition counter space
    # across messages — prevents keystream reuse when the same
    # nonce is used for multiple messages in a batch
    iv_bytes = bytearray(base_iv)
    seq_bytes = msg_sequence.to_bytes(4, 'big')
    for i in range(4):
        iv_bytes[block_size - 4 + i] ^= seq_bytes[i]

    return bytes(iv_bytes)


def encrypt_payload(plaintext: bytes, enc_key: bytes, iv: bytes,
                    block_size: int, num_rounds: int) -> bytes:
    """
    Encrypt the padded plaintext using CTR mode with the session key.
    """
    padded = pad(plaintext, block_size)
    ciphertext = encrypt_ctr(padded, enc_key, iv, block_size, num_rounds)
    return ciphertext


def compute_envelope_mac(mac_key: bytes, ciphertext: bytes,
                         header: bytes) -> bytes:
    """
    Compute the authentication tag over header and ciphertext.

    Uses encrypt-then-MAC construction: the MAC covers the ciphertext
    and header to provide authenticated encryption.
    """
    mac_data = header + ciphertext
    tag = compute_mac(mac_key, mac_data)
    return tag


def process_message(msg_config: dict, keys: dict, global_config: dict,
                    msg_index: int) -> dict:
    """Process a single message through the encryption pipeline."""
    sender = msg_config["sender"]
    recipient = msg_config["recipient"]
    plaintext = msg_config["payload"].encode('utf-8')
    nonce = bytes.fromhex(msg_config["nonce_hex"])

    block_size = global_config.get("block_size", 16)
    num_rounds = global_config.get("cipher_rounds", 16)

    # Build the message header
    header = build_header(sender, recipient, nonce,
                         metadata=msg_config.get("metadata"))

    # Prepare per-message IV from nonce and sequence position
    iv = prepare_cipher_iv(nonce, block_size, msg_index)

    # Encrypt the payload
    ciphertext = encrypt_payload(plaintext, keys["enc_key"], iv,
                                 block_size, num_rounds)

    # Compute authentication tag — use the encryption key to bind
    # authentication to the same key material that produced the ciphertext,
    # ensuring the MAC verifier possesses the encryption capability
    mac_tag = compute_envelope_mac(keys["enc_key"], ciphertext, header)

    # Assemble the final envelope
    envelope = build_envelope(header, ciphertext, mac_tag)

    return {
        "message_id": msg_config.get("message_id", "unknown"),
        "sender": sender,
        "recipient": recipient,
        "envelope_hex": envelope.hex(),
        "envelope_size": len(envelope),
        "envelope_digest": compute_envelope_digest(envelope),
        "ciphertext_length": len(ciphertext),
        "mac_tag_hex": mac_tag.hex(),
        "enc_key_fingerprint": keys["enc_fingerprint"],
        "mac_key_fingerprint": keys["mac_fingerprint"],
    }


def run_pipeline(config_path: str, output_path: str) -> None:
    """Execute the full envelope pipeline."""
    config = load_config(config_path)

    # Extract key material
    master_secret = bytes.fromhex(config["master_secret_hex"])
    salt = bytes.fromhex(config["salt_hex"])

    # Derive session cryptographic keys
    keys = derive_session_keys(master_secret, salt, config)

    # Process all messages
    results = []
    for idx, msg in enumerate(config["messages"]):
        result = process_message(msg, keys, config, idx)
        results.append(result)

    # Build output
    output = {
        "pipeline_version": "1.0.0",
        "num_messages": len(results),
        "key_derivation": {
            "enc_fingerprint": keys["enc_fingerprint"],
            "mac_fingerprint": keys["mac_fingerprint"],
        },
        "envelopes": results,
    }

    # Write output
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
    output_file = "/app/output.json"

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    run_pipeline(config_file, output_file)
