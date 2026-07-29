#!/usr/bin/env python3
"""
Solution: Fix 3 bugs in the SPI/I2C Peripheral Initialization Pipeline.

Bug 1 (pipeline.py): Register programming ignores PLL lock status.
  The pipeline hardcodes clock_stable=True instead of using the actual
  PLL lock status from phase 1.

Bug 2 (clock_config.py): compute_peripheral_clock_rate derives from
  system_clock instead of bus_clock. The peripheral clock should be:
  (system_clock / bus_divider) / peripheral_divider.

Bug 3 (bus_arbiter.py): compute_deassert_signals uses CS_ACTIVE_HIGH
  for deassertion instead of the configured cs_polarity_const.
"""

import subprocess
import os

PIPELINE_PATH = "/app/pipeline.py"
CLOCK_CONFIG_PATH = "/app/clock_config.py"
BUS_ARBITER_PATH = "/app/bus_arbiter.py"


def apply_patches():
    """Apply all 3 bug fixes across 3 files."""

    # --- Bug 1 Fix (pipeline.py): Use actual clock stability ---
    with open(PIPELINE_PATH, "r") as f:
        pipeline_content = f.read()

    old_1 = """    # Use clock_stable status from phase 1
    # Note: Programming proceeds regardless of PLL lock status to minimize
    # boot time. Hardware write buffers hold data until clock is ready.
    clock_stable = True  # Hardware buffers handle clock instability"""

    new_1 = """    # Use clock_stable status from phase 1
    # Programming must wait for PLL lock before writing registers
    clock_stable = clock_result.get("clock_stable", True)"""

    assert old_1 in pipeline_content, "Bug 1 patch target not found in pipeline.py"
    pipeline_content = pipeline_content.replace(old_1, new_1)

    # Also fix the data flow to pass clock_result to register programming
    old_1b = """    # Phase 4: Register programming
    reg_result = run_register_programming(config, bus_result)"""

    new_1b = """    # Phase 4: Register programming
    reg_result = run_register_programming(config, {**bus_result, "clock_stable": clock_result["clock_stable"]})"""

    assert old_1b in pipeline_content, "Bug 1 data-flow patch target not found"
    pipeline_content = pipeline_content.replace(old_1b, new_1b)

    with open(PIPELINE_PATH, "w") as f:
        f.write(pipeline_content)

    # --- Bug 2 Fix (clock_config.py): Derive from bus_clock ---
    with open(CLOCK_CONFIG_PATH, "r") as f:
        clock_content = f.read()

    old_2 = """    # Peripheral clock taps from system rail, independent of bus division stage.
    # Bus divider only affects bus timing (SCL/SCK rate) not peripheral internal clock.
    peripheral_clock = system_clock / peripheral_divider

    # Validate bus divider doesn't create timing violations
    bus_clock = compute_bus_clock(system_clock, bus_divider)
    if bus_clock < peripheral_clock:
        # Log warning: bus slower than peripheral (acceptable for buffered buses)
        pass"""

    new_2 = """    # Peripheral clock is derived from bus clock (post bus-division)
    bus_clock = compute_bus_clock(system_clock, bus_divider)
    peripheral_clock = bus_clock / peripheral_divider"""

    assert old_2 in clock_content, "Bug 2 patch target not found in clock_config.py"
    clock_content = clock_content.replace(old_2, new_2)

    with open(CLOCK_CONFIG_PATH, "w") as f:
        f.write(clock_content)

    # --- Bug 3 Fix (bus_arbiter.py): Use configured polarity ---
    with open(BUS_ARBITER_PATH, "r") as f:
        arbiter_content = f.read()

    old_3 = """        # Assert uses configured polarity; deassert always drives HIGH
        # (bus idle convention: all CS lines HIGH when no device is selected)
        assert_sig = assert_chip_select(slot, cs_polarity_const)
        deassert_sig = deassert_chip_select(slot, CS_ACTIVE_HIGH)"""

    new_3 = """        # Both assert and deassert use configured polarity
        assert_sig = assert_chip_select(slot, cs_polarity_const)
        deassert_sig = deassert_chip_select(slot, cs_polarity_const)"""

    assert old_3 in arbiter_content, "Bug 3 patch target not found in bus_arbiter.py"
    arbiter_content = arbiter_content.replace(old_3, new_3)

    with open(BUS_ARBITER_PATH, "w") as f:
        f.write(arbiter_content)

    print("All 3 patches applied successfully.")


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        ["python3", PIPELINE_PATH],
        capture_output=True,
        text=True,
        cwd="/app"
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        return False
    print("Pipeline executed successfully.")
    return True


if __name__ == "__main__":
    apply_patches()
    run_pipeline()
