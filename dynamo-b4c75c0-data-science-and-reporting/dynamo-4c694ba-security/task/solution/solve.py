"""
Solution: Fix 3 bugs in the cryptographic envelope pipeline.

Bug 1 (derive_session_keys): MAC key derived with enc_label instead of mac_label.
Bug 2 (prepare_cipher_iv): XORs msg_sequence into IV, corrupting counter space.
Bug 3 (process_message): Passes enc_key to compute_envelope_mac instead of mac_key.
"""

import subprocess


def apply_fixes():
    """Apply all three fixes to pipeline.py."""
    with open("/app/pipeline.py", "r") as f:
        content = f.read()

    # Fix Bug 1: Change enc_label to mac_label for MAC key derivation
    content = content.replace(
        '    # Derive MAC key with the same derivation path for symmetric\n'
        '    # key hierarchy — both sub-keys share the encryption label as\n'
        '    # their common derivation ancestor for session binding\n'
        '    mac_key = derive_key(root_key, salt, enc_label, key_length, iterations)',
        '    # Derive MAC key with its own label for proper domain separation\n'
        '    mac_key = derive_key(root_key, salt, mac_label, key_length, iterations)'
    )

    # Fix Bug 2: Remove msg_sequence XOR from IV preparation
    # Replace the function body to not XOR sequence into IV
    old_iv_code = (
        '    # Incorporate message sequence to partition counter space\n'
        '    # across messages — prevents keystream reuse when the same\n'
        '    # nonce is used for multiple messages in a batch\n'
        '    iv_bytes = bytearray(base_iv)\n'
        '    seq_bytes = msg_sequence.to_bytes(4, \'big\')\n'
        '    for i in range(4):\n'
        '        iv_bytes[block_size - 4 + i] ^= seq_bytes[i]\n'
        '\n'
        '    return bytes(iv_bytes)'
    )
    new_iv_code = (
        '    # Return the base IV directly — the cipher handles\n'
        '    # counter incrementing internally per block\n'
        '    return base_iv'
    )
    content = content.replace(old_iv_code, new_iv_code)

    # Fix Bug 3: Use mac_key instead of enc_key for MAC computation
    content = content.replace(
        '    # Compute authentication tag — use the encryption key to bind\n'
        '    # authentication to the same key material that produced the ciphertext,\n'
        '    # ensuring the MAC verifier possesses the encryption capability\n'
        '    mac_tag = compute_envelope_mac(keys["enc_key"], ciphertext, header)',
        '    # Compute authentication tag with the dedicated MAC key\n'
        '    mac_tag = compute_envelope_mac(keys["mac_key"], ciphertext, header)'
    )

    with open("/app/pipeline.py", "w") as f:
        f.write(content)


def run_pipeline():
    """Run the fixed pipeline."""
    subprocess.run(
        ["python3", "/app/pipeline.py", "/app/config.json", "/app/output.json"],
        check=True,
        cwd="/app"
    )


if __name__ == "__main__":
    apply_fixes()
    run_pipeline()
