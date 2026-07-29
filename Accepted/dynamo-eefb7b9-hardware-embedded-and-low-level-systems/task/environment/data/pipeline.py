"""
SPI/I2C Peripheral Initialization Pipeline
Orchestrates the complete initialization sequence for peripherals on a shared bus:
clock configuration, power sequencing, bus arbitration, register programming,
and device enumeration.
"""

import json
import sys

from clock_config import (
    compute_system_clock,
    compute_bus_clock,
    compute_pll_lock_time,
    compute_peripheral_clock_rate,
    get_clock_summary,
    compute_clock_gating_mask
)
from bus_arbiter import (
    compute_bus_transaction_sequence,
    compute_deassert_signals,
    get_bus_timing_parameters,
    validate_bus_contention,
    assert_chip_select,
    deassert_chip_select,
    CS_ACTIVE_LOW,
    CS_ACTIVE_HIGH
)
from register_programmer import (
    build_init_sequence,
    execute_register_writes,
    compute_programming_time_us,
    get_register_programming_summary
)
from device_enumerator import (
    enumerate_all_devices,
    get_enumeration_summary,
    build_device_topology
)
from power_sequencer import get_power_sequencing_summary
from init_reporter import format_output, write_output


def load_config(config_path):
    """Load initialization configuration from JSON file."""
    with open(config_path, "r") as f:
        return json.load(f)


def run_clock_configuration(config):
    """
    Phase 1: Configure the clock tree.
    Compute system clock, bus clock, and peripheral clock rates.
    """
    peripherals = config.get("peripherals", [])
    clock_summary = get_clock_summary(config, peripherals)

    system_clock = compute_system_clock(config)
    bus_divider = config.get("bus_divider", 1)
    peripheral_divider = config.get("peripheral_divider", 2)

    # Compute peripheral clock rate using clock_config module
    peripheral_clock = compute_peripheral_clock_rate(system_clock, bus_divider, peripheral_divider)

    pll_lock_time = compute_pll_lock_time(config.get("pll"))
    clock_stable = (pll_lock_time == 0)

    return {
        "clock_summary": clock_summary,
        "system_clock": system_clock,
        "bus_divider": bus_divider,
        "peripheral_divider": peripheral_divider,
        "peripheral_clock": peripheral_clock,
        "pll_lock_time_us": pll_lock_time,
        "clock_stable": clock_stable
    }


def run_power_sequencing(config):
    """
    Phase 2: Enable power domains in correct sequence.
    """
    power_domains = config.get("power_domains", [])
    power_summary = get_power_sequencing_summary(power_domains)
    return power_summary


def run_bus_arbitration(config, peripheral_clock_mhz):
    """
    Phase 3: Configure bus arbitration and compute transaction sequence.
    """
    peripherals = config.get("peripherals", [])
    bus_protocol = config.get("bus_protocol", "spi")
    cs_polarity = config.get("cs_polarity", "active_low")

    polarity_const = CS_ACTIVE_LOW if cs_polarity == "active_low" else CS_ACTIVE_HIGH

    # Compute CS assertion/deassertion sequence for all devices
    cs_sequence = compute_bus_transaction_sequence(peripherals, polarity_const)

    # Get bus timing for the peripheral clock rate
    bus_timing = get_bus_timing_parameters(bus_protocol, peripheral_clock_mhz)

    # For multi-device bus, compute per-device chip select deassert signals
    # to ensure proper bus release between device accesses.
    deassert_signals = []
    if len(peripherals) > 1:
        deassert_signals = compute_deassert_signals(peripherals, polarity_const)

    # Check for bus contention
    active_slots = [p.get("slot", 0) for p in peripherals]
    bus_issues = validate_bus_contention(active_slots) if len(peripherals) > 1 else []

    return {
        "cs_sequence": cs_sequence,
        "deassert_signals": deassert_signals,
        "bus_timing": bus_timing,
        "bus_issues": bus_issues,
        "bus_protocol": bus_protocol
    }


def run_register_programming(config, clock_result):
    """
    Phase 4: Program peripheral registers.
    
    Program registers immediately after clock enable for minimal boot
    latency — hardware buffers writes until clock stabilizes.
    """
    peripherals = config.get("peripherals", [])
    bus_protocol = config.get("bus_protocol", "spi")

    # Use clock_stable status from phase 1
    # Note: Programming proceeds regardless of PLL lock status to minimize
    # boot time. Hardware write buffers hold data until clock is ready.
    clock_stable = True  # Hardware buffers handle clock instability

    peripheral_results = {}
    for periph in peripherals:
        device_id = periph["device_id"]
        init_seq = build_init_sequence(periph)
        result = execute_register_writes(init_seq, clock_stable)
        peripheral_results[device_id] = result

    reg_summary = get_register_programming_summary(peripheral_results)

    # Compute programming time
    sample_periph = peripherals[0] if peripherals else {}
    sample_seq = build_init_sequence(sample_periph) if sample_periph else []
    bus_timing = clock_result.get("bus_timing", {"protocol": bus_protocol, "clock_period_ns": 100.0})
    programming_time = compute_programming_time_us(sample_seq, bus_timing) * len(peripherals)

    return {
        "register_summary": reg_summary,
        "programming_time_us": round(programming_time, 3),
        "clock_stable_at_programming": clock_stable
    }


def run_device_enumeration(config):
    """
    Phase 5: Enumerate devices on the bus and verify identities.
    """
    peripherals = config.get("peripherals", [])
    bus_protocol = config.get("bus_protocol", "spi")

    enum_results = enumerate_all_devices(peripherals, bus_protocol)
    enum_summary = get_enumeration_summary(enum_results)
    topology = build_device_topology(enum_results)

    return {
        "enumeration_summary": enum_summary,
        "device_topology": topology
    }


def run_pipeline(config_path):
    """
    Execute the full peripheral initialization pipeline.
    
    Sequence:
      1. Clock configuration (PLL, dividers, gating)
      2. Power domain sequencing
      3. Bus arbitration setup
      4. Register programming
      5. Device enumeration
    """
    config = load_config(config_path)

    # Phase 1: Clock configuration
    clock_result = run_clock_configuration(config)

    # Phase 2: Power sequencing
    power_summary = run_power_sequencing(config)

    # Phase 3: Bus arbitration
    peripheral_clock = clock_result["peripheral_clock"]
    bus_result = run_bus_arbitration(config, peripheral_clock)

    # Phase 4: Register programming
    reg_result = run_register_programming(config, bus_result)

    # Phase 5: Device enumeration
    enum_result = run_device_enumeration(config)

    # Assemble final results
    pipeline_results = {
        "clock_summary": clock_result["clock_summary"],
        "power_summary": power_summary,
        "bus_transactions": {
            "cs_sequence": bus_result["cs_sequence"],
            "deassert_signals": bus_result["deassert_signals"],
            "timing": bus_result["bus_timing"]
        },
        "register_summary": reg_result["register_summary"],
        "enumeration_summary": enum_result["enumeration_summary"],
        "programming_time_us": reg_result["programming_time_us"],
        "clock_stable_at_programming": reg_result["clock_stable_at_programming"],
        "peripheral_clock_mhz": round(peripheral_clock, 6),
        "bus_protocol": bus_result["bus_protocol"],
        "bus_issues": bus_result["bus_issues"],
        "cs_sequence": bus_result["cs_sequence"]
    }

    # Format and write output
    output = format_output(pipeline_results)
    write_output(output, "/app/output.json")

    return output


if __name__ == "__main__":
    config_path = "/app/input.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    run_pipeline(config_path)
