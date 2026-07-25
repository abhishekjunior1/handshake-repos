#!/usr/bin/env python3
"""
Solution for DMA scatter-gather descriptor chain migration pipeline.

Fixes two data-flow bugs in the orchestrator (pipeline.py) where
incorrect values are passed to individually correct module functions.
"""

import subprocess
import sys


def apply_patches():
    """Apply string-replacement patches to pipeline.py to fix all bugs."""

    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, "r") as f:
        content = f.read()

    # Fix 1: Use target bus width for address translation
    # The target controller's address space determines byte-address scaling
    content = content.replace(
        'bus_width_for_translation = source_config["bus_width"]',
        'bus_width_for_translation = target_config["bus_width"]'
    )

    # Fix 2: Use aligned transfer lengths for burst scheduling
    # The DMA engine transfers the full aligned block including padding,
    # so burst partitioning must use the padded size
    content = content.replace(
        "transfer_lengths_for_burst = [d.transfer_length for d in descriptors]",
        "transfer_lengths_for_burst = aligned_lengths"
    )

    with open(pipeline_path, "w") as f:
        f.write(content)

    print("All patches applied successfully")


def run_pipeline():
    """Execute the patched pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True, text=True, cwd="/app"
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


if __name__ == "__main__":
    apply_patches()
    run_pipeline()
