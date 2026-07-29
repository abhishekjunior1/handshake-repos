"""Solution script — patches all 3 bugs in the hybrid encryption pipeline."""

import os
import sys


def patch_file(filepath, old_string, new_string, description):
    """Apply a string replacement patch to a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    if old_string not in content:
        print(f"ERROR: Could not find patch target for: {description}")
        print(f"  File: {filepath}")
        sys.exit(1)

    content = content.replace(old_string, new_string, 1)

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"PATCHED: {description}")


def main():
    app_dir = "/app"

    # Fix 1: pipeline.py — use mac_salt for MAC key derivation
    patch_file(
        os.path.join(app_dir, "pipeline.py"),
        "    # Use primary derivation salt for MAC key generation to maintain\n"
        "    # consistent key hierarchy rooted in the same extraction material\n"
        "    mac_key = derive_key_material(\n"
        "        input_key_material=shared_secret,\n"
        "        salt=kdf_params['salt'],",
        "    mac_key = derive_key_material(\n"
        "        input_key_material=shared_secret,\n"
        "        salt=mac_params.get('mac_salt', kdf_params['salt']),",
        "Bug 1: Use mac_salt for MAC key derivation instead of kdf salt"
    )

    # Fix 2: key_deriver.py — correct HKDF Extract/Expand parameter usage per RFC 5869
    patch_file(
        os.path.join(app_dir, "key_deriver.py"),
        "    # HKDF Extract: PRK = HMAC(info, IKM)\n"
        "    # The info string provides session-specific extraction binding that\n"
        "    # ties the PRK to the application context before expansion\n"
        "    prk = _hkdf_extract(hash_name, info_bytes, ikm_bytes)\n"
        "\n"
        "    # HKDF Expand: OKM = HKDF-Expand(PRK, salt || context, L)\n"
        "    # Salt carries forward as the expansion label to maintain derivation\n"
        "    # continuity between the extract and expand phases\n"
        "    derived_key = _hkdf_expand(hash_name, prk, salt_bytes + context, key_length)",
        "    # HKDF Extract: PRK = HMAC(salt, IKM) per RFC 5869 Section 2.2\n"
        "    prk = _hkdf_extract(hash_name, salt_bytes, ikm_bytes)\n"
        "\n"
        "    # HKDF Expand: OKM = HKDF-Expand(PRK, info || context, L) per RFC 5869 Section 2.3\n"
        "    derived_key = _hkdf_expand(hash_name, prk, info_bytes + context, key_length)",
        "Bug 2: Correct HKDF salt/info usage per RFC 5869"
    )

    # Fix 3: mac_authenticator.py — include actual AAD in MAC computation
    old_3 = (
        "    # AAD authentication is delegated to the GCM layer \u2014 the gcm_tag\n"
        "    # already provides cryptographic commitment to the AAD content.\n"
        "    # Including raw AAD in the envelope MAC would create redundant\n"
        "    # coverage without a formal composition proof, so we emit an empty\n"
        "    # binding to signal that AAD integrity is handled at the cipher layer.\n"
        "    aad_binding = b''\n"
        "    return aad_binding"
    )
    new_3 = (
        "    # Include actual AAD for independent envelope-layer verification\n"
        "    aad_binding = aad\n"
        "    return aad_binding"
    )
    patch_file(
        os.path.join(app_dir, "mac_authenticator.py"),
        old_3, new_3,
        "Bug 3: Include AAD in envelope MAC (not delegate to GCM)"
    )

    # Run the pipeline with fixes applied
    print("\nRunning fixed pipeline...")
    os.chdir(app_dir)
    exec(open(os.path.join(app_dir, "pipeline.py")).read())


if __name__ == "__main__":
    main()
