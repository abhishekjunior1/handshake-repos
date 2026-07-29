"""
Solution for the event stream watermark pipeline.

Fixes two bugs:
1. pipeline.py: Uses all parsed events for watermark advancement instead of
   measurement events only
2. watermark_tracker.py: Uses max(all timestamps) instead of min(per-partition
   max) for global watermark computation
"""

import subprocess
import sys


def patch_file(filepath: str, old: str, new: str) -> None:
    """Apply a targeted string replacement patch to a file."""
    with open(filepath, "r") as f:
        content = f.read()
    if old not in content:
        print(f"WARNING: patch target not found in {filepath}")
        print(f"  Looking for: {repr(old[:80])}")
        sys.exit(1)
    content = content.replace(old, new, 1)
    with open(filepath, "w") as f:
        f.write(content)


def main():
    # Fix 1: pipeline.py — use measurement_events for watermark advancement
    patch_file(
        "/app/pipeline.py",
        "    current_watermark = advance_watermark(wm_state, parsed_events)",
        "    current_watermark = advance_watermark(wm_state, measurement_events)"
    )

    # Fix 2: watermark_tracker.py — use min(per-partition max) instead of max(all)
    patch_file(
        "/app/watermark_tracker.py",
        """    # Advance watermark using max of all event timestamps for responsive
    # advancement that minimizes output latency
    all_timestamps = [e["timestamp"] for e in events]
    new_watermark = max(all_timestamps)""",
        """    # Advance watermark as minimum of per-partition maximums to ensure
    # all partitions have progressed past this point
    new_watermark = min(state.partition_progress.values())"""
    )

    # Run the fixed pipeline
    subprocess.run([sys.executable, "/app/pipeline.py"], check=True)


if __name__ == "__main__":
    main()
