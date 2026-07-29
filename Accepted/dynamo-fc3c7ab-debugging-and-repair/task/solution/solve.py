"""
Solution for the feature flag evaluation pipeline bugs.

Patches two data-flow bugs in pipeline.py:
1. Dependency evaluation order: moves dependency resolution BEFORE rollout computation
   (dependencies determine eligibility before rollout bucketing)
2. Rollout hash computation: fixes the hash to use (device_id, flag_name) instead of
   (device_id, device_id) for independent per-flag rollout bucketing

Then executes the fixed pipeline.
"""

import subprocess
import sys
import os


def patch_pipeline():
    """Apply patches to fix the data-flow bugs in pipeline.py."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, "r") as f:
        content = f.read()

    # Bug 2: Fix rollout hash - use flag_name instead of device_id as second param
    content = content.replace(
        "hash_value = compute_hash(device_id, device_id)",
        "hash_value = compute_hash(device_id, flag_name)",
    )

    # Bug 1: Move dependency resolution before rollout computation
    # Extract Phase 2 (rollout) and Phase 3 (dependencies), then swap them

    # Find the phase markers
    phase2_start = "    # Phase 2: Compute rollout cohort assignment"
    phase3_start = "    # Phase 3: Apply dependency constraints"
    phase4_start = "    # Phase 4: Resolve mutual exclusion conflicts"

    # Split at phase boundaries
    before_p2, rest = content.split(phase2_start, 1)
    phase2_body, rest = rest.split(phase3_start, 1)
    phase3_body, after_p3 = rest.split(phase4_start, 1)

    # Reassemble with phases swapped (dependencies first, then rollout)
    content = (
        before_p2
        + "    # Phase 2: Apply dependency constraints\n"
        + "    # resolve dependencies before rollout to determine eligibility\n"
        + phase3_body
        + "    # Phase 3: Compute rollout cohort assignment\n"
        + phase2_body
        + phase4_start
        + after_p3
    )

    with open(pipeline_path, "w") as f:
        f.write(content)

    print("Patched pipeline.py: 2 data-flow bugs fixed")


def run_pipeline():
    """Execute the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout, end="")


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
