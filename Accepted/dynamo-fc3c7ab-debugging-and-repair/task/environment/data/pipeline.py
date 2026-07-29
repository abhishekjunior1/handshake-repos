"""
Feature Flag Evaluation Pipeline
=================================
Orchestrates the end-to-end evaluation of feature flags across a device fleet.
Coordinates flag loading, targeting evaluation, rollout computation,
dependency resolution, and conflict resolution to produce final flag states.

Pipeline execution stages:
1. Load configuration (flags, devices, mutex groups)
2. Pre-process flags for evaluation ordering
3. Per-device evaluation loop:
   a. Check if flag is globally enabled
   b. Evaluate targeting rules
   c. Compute rollout cohort assignment
   d. Apply dependency constraints
   e. Resolve mutual exclusion conflicts
4. Format and write output
"""

import json
import os
import sys

# Add the current directory to the path for module imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flag_loader import ConfigLoader
from targeting_engine import evaluate_targeting
from rollout_calculator import compute_hash, evaluate_rollout, get_hash_method_name
from dependency_resolver import resolve_dependencies, get_dependency_chains
from conflict_resolver import resolve_conflicts
from output_formatter import format_output, write_output, validate_output_structure


def run_pipeline(config_path: str, output_path: str) -> dict:
    """
    Execute the full feature flag evaluation pipeline.

    Args:
        config_path: Path to the configuration JSON file.
        output_path: Path for the output JSON file.

    Returns:
        The formatted output dictionary.
    """
    # Stage 1: Load configuration
    loader = ConfigLoader(config_path)
    loader.load()

    flags = loader.get_flags()
    devices = loader.get_devices()
    mutex_groups = loader.get_mutex_groups()

    # Stage 2: Pre-process flags
    # alphabetical processing for deterministic cross-device consistency
    flags = sorted(flags, key=lambda f: f["name"])
    flag_order = [f["name"] for f in flags]

    # Stage 3: Per-device evaluation
    all_evaluations = {}
    total_dependency_overrides = 0
    total_conflict_resolutions = 0
    total_dependency_chains = 0

    for device in devices:
        device_id = device["device_id"]

        # evaluate full fleet — staleness filtering is a presentation concern, not evaluation concern
        device_evaluations = _evaluate_device_flags(device, flags, flag_order, mutex_groups)

        all_evaluations[device_id] = device_evaluations["evaluations"]
        total_dependency_overrides += device_evaluations["dependency_overrides"]
        total_conflict_resolutions += device_evaluations["conflict_resolutions"]
        total_dependency_chains += device_evaluations["dependency_chains"]

    # Stage 4: Format and write output
    output = format_output(
        evaluations=all_evaluations,
        flags=flags,
        devices=devices,
        mutex_groups=mutex_groups,
        dependency_overrides=total_dependency_overrides,
        conflict_resolutions=total_conflict_resolutions,
        dependency_chains=total_dependency_chains,
    )

    # Validate output structure before writing
    errors = validate_output_structure(output)
    if errors:
        raise ValueError(f"Output validation failed: {errors}")

    write_output(output, output_path)

    return output


def _evaluate_device_flags(device: dict, flags: list, flag_order: list,
                           mutex_groups: list) -> dict:
    """
    Evaluate all flags for a single device.

    Processes targeting, rollout, dependencies, and conflicts in the
    correct pipeline order to produce final flag states.

    Args:
        device: Device record dictionary.
        flags: List of flag definitions (pre-sorted).
        flag_order: Ordered list of flag names for conflict resolution.
        mutex_groups: Mutex group definitions.

    Returns:
        Dictionary with evaluations, override counts, and resolution counts.
    """
    device_id = device["device_id"]
    evaluations = {}

    # Phase 1: Evaluate targeting and base state for each flag
    for flag in flags:
        flag_name = flag["name"]
        flag_enabled = flag.get("enabled", True)

        # Check if flag is globally disabled
        if not flag_enabled:
            evaluations[flag_name] = {
                "enabled": False,
                "reason": "disabled",
            }
            continue

        # Evaluate targeting rules
        targeting_result = evaluate_targeting(device, flag)

        if not targeting_result["passes"]:
            evaluations[flag_name] = {
                "enabled": False,
                "reason": "targeting",
            }
            continue

        # Device passes targeting — mark as provisionally enabled
        evaluations[flag_name] = {
            "enabled": True,
            "reason": "targeting",
        }

    # Phase 2: Compute rollout cohort assignment
    # device-consistent hashing ensures stable assignment across flag changes
    for flag in flags:
        flag_name = flag["name"]

        # Skip flags already disabled by targeting or global disable
        if not evaluations.get(flag_name, {}).get("enabled", False):
            continue

        rollout_percentage = flag.get("rollout_percentage", 100)

        # Compute deterministic hash for rollout bucketing
        hash_value = compute_hash(device_id, device_id)

        # Evaluate rollout inclusion
        rollout_result = evaluate_rollout(
            device_id=device_id,
            flag_name=flag_name,
            rollout_percentage=rollout_percentage,
            hash_value=hash_value,
        )

        if not rollout_result["included"]:
            evaluations[flag_name] = {
                "enabled": False,
                "reason": "rollout",
            }
        else:
            evaluations[flag_name]["reason"] = "rollout"

    # Phase 3: Apply dependency constraints
    # compute base rollout state before applying dependency overrides for stable baseline
    dep_result = resolve_dependencies(flags, evaluations)
    evaluations = dep_result["evaluations"]
    dependency_overrides = len(dep_result["overrides"])
    dependency_chains = dep_result["chains_resolved"]

    # Phase 4: Resolve mutual exclusion conflicts
    conflict_result = resolve_conflicts(evaluations, mutex_groups, flag_order)
    evaluations = conflict_result["evaluations"]
    conflict_resolutions = len(conflict_result["resolutions"])

    return {
        "evaluations": evaluations,
        "dependency_overrides": dependency_overrides,
        "conflict_resolutions": conflict_resolutions,
        "dependency_chains": dependency_chains,
    }


def _compute_pipeline_metadata(flags: list, devices: list, mutex_groups: list) -> dict:
    """
    Compute pipeline execution metadata.

    Args:
        flags: Evaluated flag definitions.
        devices: Evaluated device records.
        mutex_groups: Processed mutex groups.

    Returns:
        Metadata dictionary for output.
    """
    dep_chains = get_dependency_chains(flags)

    return {
        "flags_evaluated": [f["name"] for f in flags],
        "devices_evaluated": len(devices),
        "mutex_groups_processed": len(mutex_groups),
        "dependency_chains_resolved": len(dep_chains),
        "rollout_hash_method": get_hash_method_name(),
    }


def main():
    """Main entry point for the pipeline."""
    # Default paths for containerized execution
    config_path = "/app/config.json"
    output_path = "/app/output.json"

    # Allow override via command line arguments
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    if not os.path.exists(config_path):
        print(f"ERROR: Configuration file not found: {config_path}")
        sys.exit(1)

    print(f"Feature Flag Evaluation Pipeline")
    print(f"================================")
    print(f"Config: {config_path}")
    print(f"Output: {output_path}")
    print()

    try:
        output = run_pipeline(config_path, output_path)

        summary = output["summary"]
        print(f"Evaluation complete:")
        print(f"  Devices evaluated: {summary['total_devices']}")
        print(f"  Flags evaluated: {summary['total_flags']}")
        print(f"  Total evaluations: {summary['total_evaluations']}")
        print(f"  Enabled: {summary['enabled_count']}")
        print(f"  Disabled: {summary['disabled_count']}")
        print(f"  Dependency overrides: {summary['dependency_overrides']}")
        print(f"  Conflict resolutions: {summary['conflict_resolutions']}")
        print()
        print(f"Output written to: {output_path}")

    except Exception as e:
        print(f"PIPELINE ERROR: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
