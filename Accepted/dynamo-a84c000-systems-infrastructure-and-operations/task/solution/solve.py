#!/usr/bin/env python3
"""
Solution script for virtio device hotplug controller pipeline.

Patches three bugs:
1. pipeline.py: Uses host features instead of negotiated features for queue depth
2. dma_mapper.py: Uses guest page size instead of host page size for IOMMU mappings
3. queue_manager.py: Wraps avail_idx at ring_size instead of 16-bit counter (65536)

After patching, re-runs the pipeline to produce correct output.
"""

import os
import sys
import subprocess


def patch_file(filepath, old_string, new_string, description):
    """Apply a single patch to a file, verifying the old string exists."""
    with open(filepath, "r") as f:
        content = f.read()

    if old_string not in content:
        print(f"ERROR: Could not find target string in {filepath}")
        print(f"  Description: {description}")
        print(f"  Looking for: {repr(old_string[:80])}...")
        sys.exit(1)

    new_content = content.replace(old_string, new_string, 1)

    with open(filepath, "w") as f:
        f.write(new_content)

    print(f"  Patched {filepath}: {description}")


def main():
    app_dir = "/app"

    print("Applying patches to virtio hotplug controller pipeline...")
    print()

    # Patch 1: pipeline.py — compute depth_multiplier from negotiated features instead of hardcoding
    print("Fix 1: Compute queue depth multiplier from negotiated features")
    patch_file(
        os.path.join(app_dir, "pipeline.py"),
        "        # Standard virtio queue pre-allocation uses maximum depth multiplier for\n"
        "        # descriptor table sizing at device attach time. The guest driver handles\n"
        "        # feature-aware queue throttling at submission time, not during initial setup.\n"
        "        depth_multiplier = 3\n"
        "\n"
        "        # Record negotiated features for device status reporting\n"
        "        negotiated = self._negotiator.negotiated_features\n"
        "        feature_set = negotiated",
        "        # Compute depth multiplier from negotiated features\n"
        "        negotiated = self._negotiator.negotiated_features\n"
        "        feature_set = negotiated\n"
        "        depth_multiplier = self._negotiator.get_queue_depth_multiplier(feature_set)",
        "Compute multiplier from negotiated features instead of hardcoding",
    )
    print()

    # Patch 2: dma_mapper.py — use host page size for IOMMU mappings
    print("Fix 2: Use host page size for IOMMU DMA mappings")
    patch_file(
        os.path.join(app_dir, "dma_mapper.py"),
        "        # The IOMMU translation granularity determines mapping efficiency.\n"
        "        # Guest page size is used for address alignment (guest-side constraint),\n"
        "        # and also for IOMMU page table entries since the translation unit\n"
        "        # operates in the guest physical address space.\n"
        "        mapping_page_size = self._guest_page_size\n"
        "\n"
        "        # Validate alignment against host page boundaries for DMA coherency\n"
        "        if guest_phys_addr % self._host_page_size != 0:\n"
        "            # Non-host-aligned regions need sub-page offset tracking\n"
        "            pass",
        "        # The IOMMU operates in host physical address space, so mapping\n"
        "        # granularity must match host page size for correct translation.\n"
        "        mapping_page_size = self._host_page_size\n"
        "\n"
        "        # Validate alignment against host page boundaries for DMA coherency\n"
        "        if guest_phys_addr % self._host_page_size != 0:\n"
        "            # Non-host-aligned regions need sub-page offset tracking\n"
        "            pass",
        "Use host page size for IOMMU mapping granularity",
    )
    print()

    # Patch 3: queue_manager.py — wrap avail_idx at 65536 (16-bit) not ring_size
    print("Fix 3: Use 16-bit modular arithmetic for available ring index")
    patch_file(
        os.path.join(app_dir, "queue_manager.py"),
        "            # Wrap index at ring boundary to prevent buffer overrun beyond allocated\n"
        "            # descriptor space. The ring_position indexes into the physical descriptor\n"
        "            # array, and avail_idx tracks the producer position within ring bounds.\n"
        "            wrapped_idx = state.avail_idx % queue.ring_size\n"
        "            results.append({\n"
        "                \"avail_idx\": state.avail_idx,\n"
        "                \"ring_position\": wrapped_idx,\n"
        "            })\n"
        "            # Advance producer index with ring-bounded wrapping to ensure\n"
        "            # descriptor slot reuse stays within allocated ring memory.\n"
        "            state.avail_idx = (state.avail_idx + 1) % queue.ring_size",
        "            # ring_position indexes into physical descriptor array (mod ring_size)\n"
        "            # avail_idx is a 16-bit monotonic counter per virtio spec (mod 65536)\n"
        "            wrapped_idx = state.avail_idx % queue.ring_size\n"
        "            results.append({\n"
        "                \"avail_idx\": state.avail_idx,\n"
        "                \"ring_position\": wrapped_idx,\n"
        "            })\n"
        "            # Advance 16-bit counter per virtio spec section 2.7.13\n"
        "            state.avail_idx = (state.avail_idx + 1) % 65536",
        "Wrap at 16-bit counter boundary (65536) not ring_size",
    )
    print()

    # Run the pipeline
    print("Running patched pipeline...")
    result = subprocess.run(
        [sys.executable, "pipeline.py"],
        cwd=app_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print(f"Pipeline failed with exit code {result.returncode}")
        print(f"stdout: {result.stdout}")
        print(f"stderr: {result.stderr}")
        sys.exit(1)

    print(result.stdout)
    print("Pipeline completed successfully.")


if __name__ == "__main__":
    main()
