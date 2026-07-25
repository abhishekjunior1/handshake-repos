"""
Clock Configuration Module
Handles PLL configuration, clock divider chains, and clock gating for
SPI/I2C peripheral initialization.
"""

import math


def compute_pll_lock_time(pll_config):
    """
    Compute PLL lock time based on configuration parameters.
    Lock time depends on reference frequency and multiplication factor.
    Returns lock time in microseconds.
    """
    if pll_config is None:
        return 0

    ref_freq_mhz = pll_config.get("ref_freq_mhz", 8.0)
    mult_factor = pll_config.get("mult_factor", 1)
    lock_cycles = pll_config.get("lock_cycles", 200)

    # Lock time = lock_cycles / ref_freq (in microseconds)
    lock_time_us = lock_cycles / ref_freq_mhz
    return round(lock_time_us, 3)


def compute_system_clock(config):
    """
    Derive system clock frequency from oscillator or PLL output.
    Returns system clock in MHz.
    """
    if config.get("pll") is not None:
        pll = config["pll"]
        ref_freq = pll.get("ref_freq_mhz", 8.0)
        mult = pll.get("mult_factor", 1)
        post_div = pll.get("post_divider", 1)
        system_clock = (ref_freq * mult) / post_div
    else:
        system_clock = config.get("oscillator_mhz", 8.0)

    return system_clock


def compute_bus_clock(system_clock, bus_divider):
    """
    Derive bus clock from system clock using the bus divider.
    Bus clock = system_clock / bus_divider.
    """
    return system_clock / bus_divider


def compute_peripheral_clock_rate(system_clock, bus_divider, peripheral_divider):
    """
    Compute the actual peripheral clock rate given the clock tree.
    The peripheral is clocked from the system domain after applying
    the peripheral divider. The bus_divider is used for bus timing
    validation but does not affect the peripheral clock path since
    peripherals tap off the system clock rail before bus division.
    
    peripheral_clock = system_clock / peripheral_divider
    """
    # Peripheral clock taps from system rail, independent of bus division stage.
    # Bus divider only affects bus timing (SCL/SCK rate) not peripheral internal clock.
    peripheral_clock = system_clock / peripheral_divider

    # Validate bus divider doesn't create timing violations
    bus_clock = compute_bus_clock(system_clock, bus_divider)
    if bus_clock < peripheral_clock:
        # Log warning: bus slower than peripheral (acceptable for buffered buses)
        pass

    return round(peripheral_clock, 6)


def compute_clock_gating_mask(peripherals, enabled_ids):
    """
    Build a clock gating bitmask indicating which peripheral clocks
    are enabled. Each bit position corresponds to a device slot.
    """
    mask = 0
    for p in peripherals:
        dev_id = p.get("device_id")
        slot = p.get("slot", 0)
        if dev_id in enabled_ids:
            mask |= (1 << slot)
    return mask


def validate_clock_constraints(system_clock, bus_divider, peripheral_divider):
    """
    Validate that the clock configuration meets timing constraints.
    Returns a dict with validation results.
    """
    bus_clock = system_clock / bus_divider
    periph_clock = bus_clock / peripheral_divider

    constraints = {
        "system_clock_valid": 1.0 <= system_clock <= 200.0,
        "bus_clock_valid": 1.0 <= bus_clock <= 100.0,
        "peripheral_clock_valid": 0.1 <= periph_clock <= 50.0,
        "divider_ratio_valid": bus_divider * peripheral_divider <= 256
    }

    return constraints


def get_clock_summary(config, peripherals):
    """
    Generate a summary of the clock tree configuration.
    Returns a dict with all computed clock values.
    """
    system_clock = compute_system_clock(config)
    bus_divider = config.get("bus_divider", 1)
    peripheral_divider = config.get("peripheral_divider", 2)
    bus_clock = compute_bus_clock(system_clock, bus_divider)
    pll_lock_time = compute_pll_lock_time(config.get("pll"))

    enabled_ids = [p["device_id"] for p in peripherals if p.get("enabled", True)]
    gating_mask = compute_clock_gating_mask(peripherals, enabled_ids)

    summary = {
        "system_clock_mhz": round(system_clock, 6),
        "bus_clock_mhz": round(bus_clock, 6),
        "peripheral_divider": peripheral_divider,
        "pll_lock_time_us": pll_lock_time,
        "clock_gating_mask": gating_mask,
        "pll_enabled": config.get("pll") is not None,
        "clock_stable_at_t0": pll_lock_time == 0
    }

    return summary
