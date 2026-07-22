"""
Register Programmer Module
Handles register write sequences for peripheral initialization.
Manages write ordering, verification reads, and register banking.
"""


def build_init_sequence(peripheral_config):
    """
    Build the register initialization sequence for a peripheral device.
    Each entry specifies register address, value, and optional mask.
    """
    registers = peripheral_config.get("init_registers", [])
    sequence = []
    for reg in registers:
        entry = {
            "address": reg["address"],
            "value": reg["value"],
            "mask": reg.get("mask", 0xFF),
            "width_bits": reg.get("width_bits", 8),
            "bank": reg.get("bank", 0),
            "verify": reg.get("verify", False)
        }
        sequence.append(entry)
    return sequence


def apply_register_mask(current_value, new_value, mask):
    """
    Apply a masked write to a register.
    Bits where mask=1 take the new value, bits where mask=0 keep current.
    """
    return (current_value & ~mask) | (new_value & mask)


def execute_register_writes(init_sequence, clock_stable):
    """
    Execute the register write sequence.
    
    If clock is not stable, writes may be lost (hardware buffers are not
    active without a stable clock). Returns the list of successfully
    programmed registers.
    
    Args:
        init_sequence: list of register write entries
        clock_stable: whether the peripheral clock is stable
        
    Returns:
        dict with programmed registers and status
    """
    programmed = []
    lost_writes = []

    for entry in init_sequence:
        if not clock_stable:
            # Without stable clock, writes are lost to void
            lost_writes.append(entry["address"])
            continue

        # Simulate register write
        write_result = {
            "address": entry["address"],
            "value": entry["value"],
            "mask": entry["mask"],
            "effective_value": apply_register_mask(0x00, entry["value"], entry["mask"]),
            "bank": entry["bank"],
            "status": "written"
        }
        programmed.append(write_result)

    return {
        "programmed_count": len(programmed),
        "lost_count": len(lost_writes),
        "registers": programmed,
        "lost_addresses": lost_writes,
        "all_successful": len(lost_writes) == 0
    }


def verify_register_values(programmed_registers):
    """
    Simulate verification reads after programming.
    Returns verification results for registers marked for verify.
    """
    verification_results = []
    for reg in programmed_registers:
        if reg.get("verify", False):
            # In simulation, verify always passes if write succeeded
            verification_results.append({
                "address": reg["address"],
                "expected": reg["effective_value"],
                "actual": reg["effective_value"],
                "match": True
            })
    return verification_results


def compute_programming_time_us(init_sequence, bus_timing):
    """
    Estimate total register programming time in microseconds.
    Each register write takes: setup + data_transfer + hold cycles.
    """
    if not init_sequence:
        return 0.0

    protocol = bus_timing.get("protocol", "spi")

    if protocol == "spi":
        clock_period_ns = bus_timing.get("clock_period_ns", 100.0)
        # Each register: 8-bit address + 8-bit data = 16 clocks minimum
        bits_per_write = 16
        write_time_ns = bits_per_write * clock_period_ns
        total_ns = len(init_sequence) * (write_time_ns + bus_timing.get("setup_time_ns", 25.0))
    else:
        scl_period_us = bus_timing.get("scl_period_us", 2.5)
        # I2C: start + addr(8+1) + reg(8+1) + data(8+1) + stop = ~28 clock edges
        clocks_per_write = 28
        total_ns = len(init_sequence) * clocks_per_write * scl_period_us * 1000

    return round(total_ns / 1000.0, 3)


def get_register_programming_summary(peripherals_results):
    """
    Aggregate register programming results across all peripherals.
    """
    total_programmed = 0
    total_lost = 0
    per_device = []

    for device_id, result in peripherals_results.items():
        total_programmed += result["programmed_count"]
        total_lost += result["lost_count"]
        per_device.append({
            "device_id": device_id,
            "programmed": result["programmed_count"],
            "lost": result["lost_count"],
            "success": result["all_successful"]
        })

    return {
        "total_registers_programmed": total_programmed,
        "total_registers_lost": total_lost,
        "per_device_results": per_device,
        "all_devices_successful": total_lost == 0
    }
