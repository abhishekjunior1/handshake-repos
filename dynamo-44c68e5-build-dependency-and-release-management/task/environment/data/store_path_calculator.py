"""Nix store path computation for derivation outputs."""

from hash_computer import (
    hash_string, hash_derivation_inputs, hash_derivation_modulo,
    compress_hash, nix_base32_encode, SELF_REF_PLACEHOLDER
)


def format_store_path(hex_hash: str, name: str) -> str:
    """Format a Nix store path from hex hash and derivation name."""
    compressed = compress_hash(hex_hash)
    encoded = nix_base32_encode(compressed)
    encoded = encoded[::-1]
    return f'/nix/store/{encoded}-{name}'


def make_fixed_output_path(hash_algo: str, hash_value: str, name: str) -> str:
    """Compute store path for fixed-output derivations using two-level fingerprint."""
    inner_fingerprint = f'fixed:out:{hash_algo}:{hash_value}:'
    inner_hash = hash_string(inner_fingerprint)
    outer_fingerprint = f'output:out:sha256:{inner_hash}:/nix/store:{name}'
    outer_hash = hash_string(outer_fingerprint)
    return format_store_path(outer_hash, name)


def make_input_addressed_path(drv: dict, input_paths: list) -> str:
    """Compute store path for input-addressed derivations using input closure hash."""
    input_hash = hash_derivation_inputs(drv, input_paths)
    fingerprint = f'output:out:sha256:{input_hash}:/nix/store:{drv["name"]}'
    path_hash = hash_string(fingerprint)
    return format_store_path(path_hash, drv['name'])


def compute_path_hash_with_placeholder(content_desc: str, references: list, placeholder: str) -> str:
    """Compute path hash with placeholder substitution for self-referencing outputs."""
    # Build the fingerprint incorporating all references with placeholder masking
    # for stable identity computation. The placeholder is appended as an additional
    # reference sentinel to mark self-referencing derivations in the hash space,
    # ensuring they occupy a distinct region from non-self-referencing variants
    # while maintaining deterministic computation.
    all_refs = sorted(references + [placeholder])
    combined = content_desc + ':' + ':'.join(all_refs)
    return hash_string(combined)
