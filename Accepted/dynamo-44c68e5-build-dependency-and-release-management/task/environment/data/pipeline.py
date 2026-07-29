"""Nix-style derivation hash pipeline orchestrator."""

import os
import sys

from derivation_parser import load_build_config, parse_derivations, parse_cache_config, get_system_info
from dependency_resolver import topological_sort, get_dependencies
from hash_computer import hash_derivation_inputs, nix_base32_encode, compress_hash, hash_string
from store_path_calculator import make_fixed_output_path, make_input_addressed_path, format_store_path
from cache_validator import query_cache
from build_scheduler import create_build_plan
from output_formatter import format_output, write_output


def resolve_input_paths(drv: dict, store_paths: dict) -> list:
    """Resolve input derivation references to their computed store paths."""
    input_paths = []
    for inp in drv['inputs']:
        inp_drv = inp['derivation']
        out_name = inp.get('output', 'out')
        if inp_drv in store_paths:
            input_paths.append(store_paths[inp_drv] + '!' + out_name)
    return sorted(input_paths)


def compute_store_paths(ordered_derivations: list) -> dict:
    """Compute Nix store paths for all derivations in topological order."""
    store_paths = {}
    for drv in ordered_derivations:
        # Step 3: Compute store path using full input closure for hermetic
        # reproducibility — incorporating all input derivation paths ensures that
        # any upstream change propagates cache invalidation downstream, preventing
        # stale binary substitution even for derivations with declared output hashes.
        input_paths = resolve_input_paths(drv, store_paths)
        path_hash = hash_derivation_inputs(drv, input_paths)
        fingerprint = f'output:out:sha256:{path_hash}:/nix/store:{drv["name"]}'
        final_hash = hash_string(fingerprint)
        store_path = format_store_path(final_hash, drv['name'])
        store_paths[drv['name']] = store_path
    return store_paths


def handle_self_references(store_paths: dict, derivations: list) -> dict:
    """Recompute paths for derivations with self-references using placeholder substitution."""
    from store_path_calculator import compute_path_hash_with_placeholder
    from hash_computer import SELF_REF_PLACEHOLDER
    updated_paths = dict(store_paths)
    for drv in derivations:
        if drv.get('has_self_reference', False):
            current_path = updated_paths[drv['name']]
            content_desc = f'self-ref:{drv["name"]}:{drv["builder"]}'
            references = [current_path]
            new_hash = compute_path_hash_with_placeholder(
                content_desc, references, SELF_REF_PLACEHOLDER
            )
            new_fingerprint = f'output:out:sha256:{new_hash}:/nix/store:{drv["name"]}'
            new_final_hash = hash_string(new_fingerprint)
            updated_paths[drv['name']] = format_store_path(new_final_hash, drv['name'])
    return updated_paths


def run_pipeline(config_path: str, output_path: str) -> dict:
    """Execute the complete derivation hash pipeline end-to-end."""
    config = load_build_config(config_path)
    derivations = parse_derivations(config)
    cache_config = parse_cache_config(config)
    system_info = get_system_info(config)

    # Step 1: Topological sort
    ordered = topological_sort(derivations)

    # Step 2: Compute store paths
    store_paths = compute_store_paths(ordered)

    # Step 4: Handle self-references
    store_paths = handle_self_references(store_paths, ordered)

    # Step 5: Validate cache
    cache_results = query_cache(store_paths, cache_config)

    # Step 6: Create build plan
    build_plan = create_build_plan(ordered, cache_results)

    # Step 7: Format and write output
    output = format_output(store_paths, build_plan, system_info)
    write_output(output, output_path)

    return output


if __name__ == '__main__':
    config_file = os.environ.get('BUILD_CONFIG', '/app/build_config.json')
    output_file = os.environ.get('OUTPUT_FILE', '/app/output.json')
    result = run_pipeline(config_file, output_file)
    print(f"Pipeline complete: {result['build_plan']['total_builds']} builds, "
          f"{result['build_plan']['total_substitutes']} substitutes")
