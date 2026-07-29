"""
Output Formatter Module
=======================
Formats feature flag evaluation results into the standardized output format.
Produces a JSON structure containing per-device evaluations, summary statistics,
and pipeline metadata for downstream consumption and validation.
"""

import json
from typing import Dict, List


def format_output(evaluations: Dict[str, Dict[str, dict]], flags: list,
                  devices: list, mutex_groups: list,
                  dependency_overrides: int, conflict_resolutions: int,
                  dependency_chains: int) -> dict:
    """
    Format evaluation results into the standard output structure.

    Args:
        evaluations: Nested dict {device_id: {flag_name: {enabled, reason}}}.
        flags: List of flag definitions that were evaluated.
        devices: List of device records that were evaluated.
        mutex_groups: List of mutex group definitions.
        dependency_overrides: Count of dependency override events.
        conflict_resolutions: Count of conflict resolution events.
        dependency_chains: Number of dependency chains resolved.

    Returns:
        Formatted output dictionary ready for JSON serialization.
    """
    # Compute summary statistics
    total_devices = len(devices)
    total_flags = len(flags)
    total_evaluations = 0
    enabled_count = 0
    disabled_count = 0

    for device_id, device_evals in evaluations.items():
        for flag_name, eval_result in device_evals.items():
            total_evaluations += 1
            if eval_result["enabled"]:
                enabled_count += 1
            else:
                disabled_count += 1

    # Build metadata
    flag_names = [f["name"] for f in flags]

    output = {
        "evaluations": evaluations,
        "summary": {
            "total_devices": total_devices,
            "total_flags": total_flags,
            "total_evaluations": total_evaluations,
            "enabled_count": enabled_count,
            "disabled_count": disabled_count,
            "dependency_overrides": dependency_overrides,
            "conflict_resolutions": conflict_resolutions,
        },
        "metadata": {
            "flags_evaluated": flag_names,
            "devices_evaluated": total_devices,
            "mutex_groups_processed": len(mutex_groups),
            "dependency_chains_resolved": dependency_chains,
            "rollout_hash_method": "device_flag_composite",
        },
    }

    return output


def write_output(output: dict, output_path: str) -> str:
    """
    Write formatted output to a JSON file.

    Args:
        output: Formatted output dictionary.
        output_path: File path for the output JSON.

    Returns:
        The output file path that was written.
    """
    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    return output_path


def validate_output_structure(output: dict) -> List[str]:
    """
    Validate that output conforms to the expected schema.

    Returns a list of validation errors (empty if valid).
    """
    errors = []

    required_top_keys = ["evaluations", "summary", "metadata"]
    for key in required_top_keys:
        if key not in output:
            errors.append(f"Missing top-level key: {key}")

    if "summary" in output:
        required_summary_keys = [
            "total_devices", "total_flags", "total_evaluations",
            "enabled_count", "disabled_count",
            "dependency_overrides", "conflict_resolutions",
        ]
        for key in required_summary_keys:
            if key not in output["summary"]:
                errors.append(f"Missing summary key: {key}")

    if "metadata" in output:
        required_meta_keys = [
            "flags_evaluated", "devices_evaluated",
            "mutex_groups_processed", "dependency_chains_resolved",
            "rollout_hash_method",
        ]
        for key in required_meta_keys:
            if key not in output["metadata"]:
                errors.append(f"Missing metadata key: {key}")

    return errors
