"""Solution: patches 3 bugs across 3 files in the DMA controller pipeline."""

import subprocess
import sys


def patch_file(filepath, old_str, new_str):
    """Replace old_str with new_str in filepath."""
    with open(filepath, "r") as f:
        content = f.read()
    if old_str not in content:
        print(f"ERROR: Could not find patch target in {filepath}")
        sys.exit(1)
    content = content.replace(old_str, new_str)
    with open(filepath, "w") as f:
        f.write(content)
    print(f"Patched {filepath}")


def main():
    # Bug 1: pipeline.py — hardcoded burst_size = 16
    # Fix: compute optimal burst from address alignment and transfer size
    patch_file(
        "/app/pipeline.py",
        "        # Standard AXI4 burst length for maximum bus utilization —\n"
        "        # peripheral adapts via flow control\n"
        "        burst_size = 16",
        "        # Compute optimal burst from address alignment constraints\n"
        "        burst_size = compute_optimal_burst(src_addr, transfer_size, max_burst)"
    )

    # Bug 2: scatter_gather.py — uses descriptor_size for transfer count
    # Fix: use payload_size for computing segment transfers
    patch_file(
        "/app/scatter_gather.py",
        "        # Compute transfers for this segment based on descriptor granularity\n"
        "        seg_transfers = max(1, seg_size // descriptor_size)",
        "        # Compute transfers for this segment based on payload granularity\n"
        "        seg_transfers = max(1, seg_size // payload_size)"
    )

    # Bug 3: channel_arbiter.py — inverted preemption comparison
    # Fix: lower priority number = higher priority = should preempt
    patch_file(
        "/app/channel_arbiter.py",
        "    # Ascending priority comparison for preemption fairness\n"
        "    return candidate_pri > current_pri",
        "    # Lower numeric value = higher priority = should preempt\n"
        "    return candidate_pri < current_pri"
    )

    # Run the pipeline
    result = subprocess.run(
        ["python3", "/app/pipeline.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        sys.exit(1)
    print("Pipeline executed successfully")


if __name__ == "__main__":
    main()
