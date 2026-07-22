"""
Solution: patches 3 bugs across pipeline.py, cache_validator.py, store_path_calculator.py.
"""

import os
import subprocess
import sys


def patch_all():
    """Apply all 3 fixes."""
    # Fix 1: pipeline.py - dispatch fixed-output derivations to make_fixed_output_path
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    content = content.replace(
        """    store_paths = {}
    for drv in ordered_derivations:
        # Step 3: Compute store path using full input closure for hermetic
        # reproducibility \u2014 incorporating all input derivation paths ensures that
        # any upstream change propagates cache invalidation downstream, preventing
        # stale binary substitution even for derivations with declared output hashes.
        input_paths = resolve_input_paths(drv, store_paths)
        path_hash = hash_derivation_inputs(drv, input_paths)
        fingerprint = f'output:out:sha256:{path_hash}:/nix/store:{drv["name"]}'
        final_hash = hash_string(fingerprint)
        store_path = format_store_path(final_hash, drv['name'])
        store_paths[drv['name']] = store_path""",
        """    store_paths = {}
    for drv in ordered_derivations:
        if drv.get('is_fixed_output', False):
            store_paths[drv['name']] = make_fixed_output_path(
                drv['hash_algo'], drv['output_hash'], drv['name'])
            continue
        input_paths = resolve_input_paths(drv, store_paths)
        path_hash = hash_derivation_inputs(drv, input_paths)
        fingerprint = f'output:out:sha256:{path_hash}:/nix/store:{drv["name"]}'
        final_hash = hash_string(fingerprint)
        store_path = format_store_path(final_hash, drv['name'])
        store_paths[drv['name']] = store_path"""
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)
    print("Fix 1 applied (pipeline.py)")

    # Fix 2: cache_validator.py - always use NARHash regardless of compression
    with open('/app/cache_validator.py', 'r') as f:
        content = f.read()

    content = content.replace(
        """def _extract_integrity_hash(narinfo: dict) -> str:
    \"\"\"Extract the appropriate integrity hash from narinfo metadata.\"\"\"
    # Prefer the file-level hash when available as it covers the full transfer
    # payload including compression envelope; fall back to NAR hash for
    # uncompressed entries where both are equivalent.
    if narinfo.get('Compression', 'none') != 'none':
        return narinfo.get('FileHash', '')
    return narinfo.get('NARHash', narinfo.get('FileHash', ''))""",
        """def _extract_integrity_hash(narinfo: dict) -> str:
    \"\"\"Extract the appropriate integrity hash from narinfo metadata.\"\"\"
    # Always use NARHash - canonical content hash of uncompressed NAR stream,
    # independent of transfer compression method.
    return narinfo.get('NARHash', '')"""
    )

    with open('/app/cache_validator.py', 'w') as f:
        f.write(content)
    print("Fix 2 applied (cache_validator.py)")

    # Fix 3: store_path_calculator.py - replace self-refs with placeholder, don't append
    with open('/app/store_path_calculator.py', 'r') as f:
        content = f.read()

    content = content.replace(
        """def compute_path_hash_with_placeholder(content_desc: str, references: list, placeholder: str) -> str:
    \"\"\"Compute path hash with placeholder substitution for self-referencing outputs.\"\"\"
    # Build the fingerprint incorporating all references with placeholder masking
    # for stable identity computation. The placeholder is appended as an additional
    # reference sentinel to mark self-referencing derivations in the hash space,
    # ensuring they occupy a distinct region from non-self-referencing variants
    # while maintaining deterministic computation.
    all_refs = sorted(references + [placeholder])
    combined = content_desc + ':' + ':'.join(all_refs)
    return hash_string(combined)""",
        """def compute_path_hash_with_placeholder(content_desc: str, references: list, placeholder: str) -> str:
    \"\"\"Compute path hash with placeholder substitution for self-referencing outputs.\"\"\"
    # Replace self-references with placeholder to break circular dependency.
    masked_refs = [placeholder if ref in references else ref for ref in references]
    combined = content_desc + ':' + ':'.join(sorted(masked_refs))
    return hash_string(combined)"""
    )

    with open('/app/store_path_calculator.py', 'w') as f:
        f.write(content)
    print("Fix 3 applied (store_path_calculator.py)")


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        [sys.executable, '/app/pipeline.py'],
        cwd='/app',
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    if result.returncode != 0:
        sys.exit(result.returncode)


if __name__ == '__main__':
    patch_all()
    run_pipeline()
