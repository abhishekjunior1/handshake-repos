"""Burst Calculator — Computes optimal DMA burst sizes.

Determines the maximum burst length that satisfies alignment constraints,
transfer size boundaries, and AXI4 protocol limits. Burst transactions
must not cross 4KB address boundaries per AXI specification.
"""

import math


AXI4_BOUNDARY = 4096  # 4KB boundary crossing limit
MAX_AXI4_BURST = 256  # Maximum AXI4 burst length (beats)
BURST_SIZES = [1, 2, 4, 8, 16, 32, 64, 128, 256]


def compute_optimal_burst(address, transfer_size, max_burst):
    """Compute the optimal burst size for a given transfer.

    The burst must satisfy:
    1. Not exceed max_burst configuration
    2. Not cross a 4KB AXI4 address boundary
    3. Be a power-of-2 aligned to the start address
    4. Not exceed remaining transfer bytes

    Args:
        address: Source/destination physical address.
        transfer_size: Total bytes remaining to transfer.
        max_burst: Maximum burst length from controller config.

    Returns:
        Optimal burst size in bytes.
    """
    if transfer_size <= 0:
        return 1

    # Limit to configured maximum
    burst = min(max_burst, MAX_AXI4_BURST)

    # Alignment constraint: burst must be power-of-2 aligned
    if address > 0:
        alignment = address & (-address)  # lowest set bit
        burst = min(burst, alignment)

    # 4KB boundary constraint
    offset_in_page = address % AXI4_BOUNDARY
    remaining_in_page = AXI4_BOUNDARY - offset_in_page
    burst = min(burst, remaining_in_page)

    # Don't exceed transfer size
    burst = min(burst, transfer_size)

    # Round down to nearest power of 2
    burst = _floor_power_of_2(burst)

    return max(1, burst)


def compute_transfer_beats(transfer_size, burst_size, data_width=4):
    """Calculate total number of bus beats for a transfer.

    Args:
        transfer_size: Total bytes to transfer.
        burst_size: Burst size in bytes.
        data_width: Bus data width in bytes (default 4 for 32-bit).

    Returns:
        Total number of beats required.
    """
    bytes_per_beat = data_width
    beats_per_burst = max(1, burst_size // bytes_per_beat)
    total_beats = math.ceil(transfer_size / bytes_per_beat)
    return total_beats


def compute_burst_efficiency(address, transfer_size, burst_size):
    """Calculate burst utilization efficiency.

    Measures how well the burst size utilizes the bus bandwidth,
    accounting for partial final bursts and alignment waste.

    Args:
        address: Transfer start address.
        transfer_size: Total bytes to transfer.
        burst_size: Selected burst size.

    Returns:
        Efficiency ratio between 0.0 and 1.0.
    """
    if transfer_size <= 0 or burst_size <= 0:
        return 0.0

    full_bursts = transfer_size // burst_size
    remainder = transfer_size % burst_size

    total_bus_cycles = full_bursts + (1 if remainder > 0 else 0)
    total_capacity = total_bus_cycles * burst_size

    efficiency = transfer_size / total_capacity if total_capacity > 0 else 0.0
    return round(efficiency, 6)


def validate_burst_parameters(address, burst_size, transfer_size):
    """Validate that burst parameters meet AXI4 protocol requirements.

    Args:
        address: Transfer start address.
        burst_size: Proposed burst size.
        transfer_size: Total transfer size.

    Returns:
        Dict with 'valid' boolean and 'violations' list.
    """
    violations = []

    if burst_size not in BURST_SIZES:
        violations.append(f"burst_size {burst_size} not power-of-2")

    if burst_size > MAX_AXI4_BURST:
        violations.append(f"burst_size {burst_size} exceeds AXI4 max {MAX_AXI4_BURST}")

    offset = address % AXI4_BOUNDARY
    if offset + burst_size > AXI4_BOUNDARY:
        violations.append(f"burst crosses 4KB boundary at address 0x{address:08x}")

    if address % burst_size != 0:
        violations.append(f"address 0x{address:08x} not aligned to burst_size {burst_size}")

    return {
        "valid": len(violations) == 0,
        "violations": violations
    }


def _floor_power_of_2(n):
    """Round down to nearest power of 2."""
    if n <= 0:
        return 1
    n = int(n)
    n |= n >> 1
    n |= n >> 2
    n |= n >> 4
    n |= n >> 8
    n |= n >> 16
    return (n + 1) >> 1
