"""
DMA Burst Size Calculator

Computes optimal burst transfer sizes for descriptor chain migration.
Burst sizing must account for:
  - Target bus width constraints
  - Maximum burst length supported by the controller
  - Transfer length alignment to burst boundaries
  - AXI/AHB protocol requirements for burst transactions

The burst size determines how many beats occur in a single bus transaction.
A beat transfers bus_width_bytes of data. The burst length (number of beats)
must be chosen so that the total transfer can be evenly partitioned into
complete bursts with an optional final partial burst.
"""

import math


# Standard AXI burst lengths (powers of 2)
AXI_BURST_LENGTHS = [1, 2, 4, 8, 16]

# Maximum single burst transfer for AXI4 protocol
AXI4_MAX_BURST_BYTES = 4096


def compute_burst_parameters(transfer_length, bus_width_bytes, max_burst_length=16):
    """
    Compute optimal burst parameters for a single descriptor transfer.

    Selects the largest burst length that:
      1. Does not exceed max_burst_length beats
      2. Produces a burst size <= AXI4_MAX_BURST_BYTES
      3. Evenly divides the aligned transfer length when possible

    Args:
        transfer_length: total bytes to transfer (must be already aligned)
        bus_width_bytes: target bus width in bytes
        max_burst_length: maximum beats per burst (default 16 for AXI4)

    Returns:
        dict with:
          - burst_length: number of beats per burst transaction
          - burst_size_bytes: bytes per burst (burst_length * bus_width_bytes)
          - full_bursts: number of complete bursts needed
          - remainder_bytes: bytes in final partial burst (0 if evenly divides)
          - total_beats: total bus beats for the entire transfer
    """
    if transfer_length <= 0:
        raise ValueError(f"Transfer length must be positive, got {transfer_length}")
    if bus_width_bytes <= 0:
        raise ValueError(f"Bus width must be positive, got {bus_width_bytes}")

    # Find optimal burst length from allowed AXI lengths
    optimal_burst = 1
    for bl in AXI_BURST_LENGTHS:
        if bl > max_burst_length:
            break
        burst_bytes = bl * bus_width_bytes
        if burst_bytes > AXI4_MAX_BURST_BYTES:
            break
        # Prefer burst lengths that evenly divide the transfer
        if transfer_length % burst_bytes == 0:
            optimal_burst = bl
        elif bl <= max_burst_length and burst_bytes <= AXI4_MAX_BURST_BYTES:
            # Still a valid burst, just won't divide evenly
            if optimal_burst == 1:
                optimal_burst = bl

    burst_size = optimal_burst * bus_width_bytes
    full_bursts = transfer_length // burst_size
    remainder = transfer_length % burst_size
    total_beats = full_bursts * optimal_burst
    if remainder > 0:
        total_beats += math.ceil(remainder / bus_width_bytes)

    return {
        "burst_length": optimal_burst,
        "burst_size_bytes": burst_size,
        "full_bursts": full_bursts,
        "remainder_bytes": remainder,
        "total_beats": total_beats
    }


def compute_chain_burst_schedule(transfer_lengths, bus_width_bytes, max_burst_length=16):
    """
    Compute burst parameters for every descriptor in the chain.

    Args:
        transfer_lengths: list of byte counts for each descriptor
        bus_width_bytes: target bus width in bytes
        max_burst_length: max beats per burst

    Returns:
        list of burst parameter dicts (same order as input)
    """
    schedule = []
    for length in transfer_lengths:
        params = compute_burst_parameters(length, bus_width_bytes, max_burst_length)
        schedule.append(params)
    return schedule


def compute_total_bus_cycles(burst_schedule):
    """
    Sum total bus beats across all descriptors in the chain.
    Includes inter-burst overhead (1 cycle per burst boundary for address phase).

    Args:
        burst_schedule: list of burst parameter dicts from compute_chain_burst_schedule

    Returns:
        dict with total_beats, total_bursts, overhead_cycles, effective_cycles
    """
    total_beats = 0
    total_bursts = 0

    for params in burst_schedule:
        total_beats += params["total_beats"]
        full = params["full_bursts"]
        has_remainder = 1 if params["remainder_bytes"] > 0 else 0
        total_bursts += full + has_remainder

    # Each burst requires 1 address-phase cycle overhead
    overhead_cycles = total_bursts

    return {
        "total_beats": total_beats,
        "total_bursts": total_bursts,
        "overhead_cycles": overhead_cycles,
        "effective_cycles": total_beats + overhead_cycles
    }


def validate_burst_boundary_crossing(start_address, transfer_length, burst_size_bytes):
    """
    Check if a transfer crosses a 4KB AXI boundary.
    AXI protocol requires bursts not to cross 4KB address boundaries.

    Args:
        start_address: starting byte address of the transfer
        transfer_length: number of bytes to transfer
        burst_size_bytes: size of each burst in bytes

    Returns:
        dict with crosses_boundary (bool), boundary_address, split_needed (bool)
    """
    boundary_4k = 4096
    start_page = start_address // boundary_4k
    end_address = start_address + transfer_length - 1
    end_page = end_address // boundary_4k

    crosses = start_page != end_page
    boundary_addr = (start_page + 1) * boundary_4k if crosses else None

    return {
        "crosses_boundary": crosses,
        "boundary_address": boundary_addr,
        "split_needed": crosses and burst_size_bytes > (boundary_addr - start_address)
    }
