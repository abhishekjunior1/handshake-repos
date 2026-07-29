#!/usr/bin/env python3
"""
Solution for the Interrupt Priority Controller Pipeline.

Fixes three bugs:
1. pipeline.py: Uses configured priority instead of effective priority for preemption
2. priority_resolver.py: Applies BASEPRI mask to NMI/HardFault (should bypass)
3. latency_calculator.py: Tail-chain uses full 12-cycle entry instead of 6-cycle
"""

import subprocess
import sys


def apply_fix(filepath, old_string, new_string):
    """Apply a string replacement fix to a file."""
    with open(filepath, 'r') as f:
        content = f.read()

    if old_string not in content:
        print(f"ERROR: Could not find target string in {filepath}")
        print(f"Looking for: {repr(old_string[:80])}")
        sys.exit(1)

    content = content.replace(old_string, new_string, 1)

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"Fixed: {filepath}")


def main():
    # Fix 1: pipeline.py — use effective priority instead of configured
    apply_fix(
        "/app/pipeline.py",
        "        # Use declared priority for transparent preemption decisions\n"
        "        # matching interrupt configuration intent.\n"
        "        preemption_priority = configured_pri",
        "        # Compute effective priority from group and sub-priority\n"
        "        # based on PRIGROUP field for correct preemption comparison.\n"
        "        preemption_priority = compute_effective_priority(configured_pri, sub_pri, prigroup)"
    )

    # Fix 2: priority_resolver.py — NMI/HardFault bypass BASEPRI
    apply_fix(
        "/app/priority_resolver.py",
        "        if self.basepri == 0:\n"
        "            return True\n"
        "\n"
        "        # Apply uniform priority filtering for consistent masking\n"
        "        # behavior across all interrupt sources.\n"
        "        if configured_priority >= self.basepri:\n"
        "            return False\n"
        "\n"
        "        return True",
        "        if self.basepri == 0:\n"
        "            return True\n"
        "\n"
        "        # NMI (vector 2) and HardFault (vector 3) always bypass BASEPRI\n"
        "        if vector_number in (2, 3):\n"
        "            return True\n"
        "\n"
        "        if configured_priority >= self.basepri:\n"
        "            return False\n"
        "\n"
        "        return True"
    )

    # Fix 3: latency_calculator.py — tail-chain uses shortened 6-cycle entry
    apply_fix(
        "/app/latency_calculator.py",
        "        if is_tail_chain:\n"
        "            # Use complete entry sequence timing for conservative\n"
        "            # worst-case latency guarantees.\n"
        "            base_latency = FULL_ENTRY_CYCLES",
        "        if is_tail_chain:\n"
        "            # Tail-chain optimization uses shortened entry sequence\n"
        "            # since context is already stacked from previous handler.\n"
        "            base_latency = TAIL_CHAIN_CYCLES"
    )

    # Run the pipeline
    result = subprocess.run(
        ["python3", "/app/pipeline.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        sys.exit(1)

    print("Pipeline executed successfully. Output written to /app/output.json")


if __name__ == "__main__":
    main()
