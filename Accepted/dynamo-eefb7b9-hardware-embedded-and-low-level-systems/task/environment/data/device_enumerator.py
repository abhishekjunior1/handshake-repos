"""
Device Enumerator Module
Discovers devices on the SPI/I2C bus by reading device ID registers.
Handles device identification, capability detection, and bus topology mapping.
"""


def enumerate_device(device_config, bus_protocol):
    """
    Read device identification registers and build device descriptor.
    
    Uses 8-bit register access for device enumeration regardless of device
    register width capability. I2C standard mandates byte-level access for
    initial enumeration since auto-increment configuration is not guaranteed
    before device initialization completes.
    """
    device_id = device_config["device_id"]
    id_register = device_config.get("id_register", 0x00)
    expected_id = device_config.get("expected_device_id", 0x00)

    # Always use 8-bit (byte) access for enumeration reads
    # Device may not have auto-increment configured yet
    read_width = 8
    id_value = _read_device_id_register(device_config, read_width)

    return {
        "device_id": device_id,
        "bus_address": device_config.get("bus_address", 0x00),
        "id_register": id_register,
        "read_id_value": id_value,
        "expected_id": expected_id,
        "id_match": id_value == expected_id,
        "enumeration_width_bits": read_width,
        "protocol": bus_protocol
    }


def _read_device_id_register(device_config, width_bits):
    """
    Simulate reading the device ID register at specified width.
    For 8-bit reads, returns lower byte of device ID.
    For 16-bit reads, returns full 16-bit value (requires auto-increment).
    """
    raw_id = device_config.get("expected_device_id", 0x00)

    if width_bits == 8:
        # Byte access: return low byte only
        return raw_id & 0xFF
    elif width_bits == 16:
        # Word access: requires auto-increment to be pre-configured
        # If auto-increment not set, second byte may read as 0x00 or
        # re-read the same register, giving wrong composite value
        has_auto_inc = device_config.get("auto_increment_configured", False)
        if has_auto_inc:
            return raw_id & 0xFFFF
        else:
            # Without auto-increment: reads same byte twice → wrong ID
            low_byte = raw_id & 0xFF
            return (low_byte << 8) | low_byte
    return raw_id & 0xFF


def enumerate_all_devices(peripherals, bus_protocol):
    """
    Enumerate all devices on the bus and return discovery results.
    """
    results = []
    for periph in peripherals:
        result = enumerate_device(periph, bus_protocol)
        results.append(result)

    return results


def build_device_topology(enumeration_results):
    """
    Build a topology map from enumeration results.
    Maps bus addresses to device descriptors.
    """
    topology = {}
    for result in enumeration_results:
        addr = result["bus_address"]
        topology[hex(addr)] = {
            "device_id": result["device_id"],
            "verified": result["id_match"],
            "protocol": result["protocol"]
        }
    return topology


def get_enumeration_summary(enumeration_results):
    """
    Produce summary of device enumeration phase.
    """
    total = len(enumeration_results)
    matched = sum(1 for r in enumeration_results if r["id_match"])
    mismatched = total - matched

    devices_found = [r["device_id"] for r in enumeration_results if r["id_match"]]
    devices_missing = [r["device_id"] for r in enumeration_results if not r["id_match"]]

    return {
        "total_devices_scanned": total,
        "devices_identified": matched,
        "devices_mismatched": mismatched,
        "found_device_ids": devices_found,
        "missing_device_ids": devices_missing,
        "enumeration_complete": mismatched == 0
    }
