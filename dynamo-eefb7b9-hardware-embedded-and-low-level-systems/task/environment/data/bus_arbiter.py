"""
Bus Arbiter Module
Manages SPI/I2C bus arbitration, chip select signals, and transaction scheduling
for shared peripheral buses.
"""


# Chip select polarity constants
CS_ACTIVE_LOW = 0
CS_ACTIVE_HIGH = 1

# Bus states
BUS_IDLE = "idle"
BUS_ACTIVE = "active"
BUS_ARBITRATING = "arbitrating"


def compute_chip_select_state(device_slot, active_device_slot, cs_polarity):
    """
    Compute the chip select line state for a given device.
    
    In active-low logic (standard SPI):
      - CS is driven LOW to select a device
      - CS is driven HIGH to deselect a device
    
    In active-high logic (rare, active-high peripherals):
      - CS is driven HIGH to select
      - CS is driven LOW to deselect
    
    Returns 1 for line high, 0 for line low.
    """
    is_selected = (device_slot == active_device_slot)

    if cs_polarity == CS_ACTIVE_LOW:
        # Active-low: selected = low (0), deselected = high (1)
        return 0 if is_selected else 1
    else:
        # Active-high: selected = high (1), deselected = low (0)
        return 1 if is_selected else 0


def assert_chip_select(device_slot, cs_polarity):
    """
    Generate the bus signal to ASSERT (activate) chip select for a device.
    Returns the signal level to drive the CS pin.
    """
    if cs_polarity == CS_ACTIVE_LOW:
        return 0  # Drive low to select
    else:
        return 1  # Drive high to select


def deassert_chip_select(device_slot, cs_polarity):
    """
    Generate the bus signal to DEASSERT (deactivate) chip select for a device.
    Returns the signal level to drive the CS pin.
    
    For active-low: drive HIGH to deselect.
    For active-high: drive LOW to deselect.
    """
    if cs_polarity == CS_ACTIVE_LOW:
        return 1  # Drive high to deselect
    else:
        return 0  # Drive low to deselect


def arbitrate_bus_access(pending_transactions, priority_scheme="round_robin"):
    """
    Select the next transaction to execute from pending requests.
    Supports round-robin and priority-based arbitration.
    """
    if not pending_transactions:
        return None

    if priority_scheme == "priority":
        # Higher priority number = higher urgency
        sorted_txns = sorted(pending_transactions, key=lambda t: t.get("priority", 0), reverse=True)
        return sorted_txns[0]
    else:
        # Round-robin: take first in queue
        return pending_transactions[0]


def compute_bus_transaction_sequence(peripherals, cs_polarity):
    """
    Compute the full chip select assertion/deassertion sequence for
    initializing all peripherals on the bus.
    
    For each device:
      1. Assert CS (select device)
      2. Perform register writes
      3. Deassert CS (deselect device)
    
    Returns list of (device_id, assert_signal, deassert_signal) tuples.
    """
    sequence = []
    for periph in peripherals:
        device_id = periph["device_id"]
        slot = periph.get("slot", 0)
        assert_sig = assert_chip_select(slot, cs_polarity)
        deassert_sig = deassert_chip_select(slot, cs_polarity)
        sequence.append({
            "device_id": device_id,
            "slot": slot,
            "cs_assert": assert_sig,
            "cs_deassert": deassert_sig,
            "cs_polarity": "active_low" if cs_polarity == CS_ACTIVE_LOW else "active_high"
        })
    return sequence


def validate_bus_contention(active_devices, max_bus_devices=8):
    """
    Check for bus contention issues:
    - Multiple devices selected simultaneously
    - Exceeding maximum bus device count
    """
    issues = []
    if len(active_devices) > 1:
        issues.append({
            "type": "multi_select",
            "message": f"Multiple devices active: {active_devices}",
            "severity": "error"
        })
    if len(active_devices) > max_bus_devices:
        issues.append({
            "type": "bus_overload",
            "message": f"Bus device count {len(active_devices)} exceeds max {max_bus_devices}",
            "severity": "error"
        })
    return issues


def compute_deassert_signals(peripherals, cs_polarity_const):
    """
    Compute chip select deassert signals for all devices on a multi-device bus.
    Used during bus release between consecutive device accesses.
    
    The deassert signal drives the bus to idle state. For proper bus release,
    CS lines are driven to their inactive state (HIGH for idle bus convention).
    The cs_polarity_const determines assertion logic; deassertion always returns
    the line to logical HIGH (bus-idle convention).
    """
    deassert_signals = []
    for periph in peripherals:
        slot = periph.get("slot", 0)
        # Assert uses configured polarity; deassert always drives HIGH
        # (bus idle convention: all CS lines HIGH when no device is selected)
        assert_sig = assert_chip_select(slot, cs_polarity_const)
        deassert_sig = deassert_chip_select(slot, CS_ACTIVE_HIGH)
        deassert_signals.append({
            "device_id": periph["device_id"],
            "slot": slot,
            "deassert_level": deassert_sig
        })
    return deassert_signals


def get_bus_timing_parameters(bus_protocol, peripheral_clock_mhz):
    """
    Compute bus timing parameters based on protocol and clock rate.
    SPI: clock period, setup time, hold time
    I2C: SCL period, start/stop setup
    """
    if bus_protocol == "spi":
        clock_period_ns = 1000.0 / peripheral_clock_mhz
        setup_time_ns = clock_period_ns * 0.25
        hold_time_ns = clock_period_ns * 0.25
        return {
            "protocol": "spi",
            "clock_period_ns": round(clock_period_ns, 2),
            "setup_time_ns": round(setup_time_ns, 2),
            "hold_time_ns": round(hold_time_ns, 2),
            "max_freq_mhz": peripheral_clock_mhz
        }
    else:  # i2c
        # I2C standard mode: 100kHz, fast mode: 400kHz
        scl_freq_khz = min(peripheral_clock_mhz * 1000 / 4, 400)
        scl_period_us = 1000.0 / scl_freq_khz
        return {
            "protocol": "i2c",
            "scl_freq_khz": round(scl_freq_khz, 2),
            "scl_period_us": round(scl_period_us, 4),
            "setup_time_us": round(scl_period_us * 0.3, 4),
            "max_freq_khz": 400.0
        }
