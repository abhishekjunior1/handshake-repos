"""
DMA Alignment Engine

Handles address and transfer alignment for target architecture constraints.
Computes aligned transfer sizes and padding for descriptors that do not
meet hardware alignment requirements.
"""

import math


def compute_aligned_length(transfer_length, alignment_boundary):
    """
    Round up a transfer length to the next alignment boundary.

    If transfer_length is already a multiple of alignment_boundary,
    returns it unchanged. Otherwise rounds up.

    Args:
        transfer_length: original byte count
        alignment_boundary: required alignment in bytes

    Returns:
        aligned length (>= transfer_length, multiple of alignment_boundary)
    """
    if alignment_boundary <= 0:
        raise ValueError(f"Alignment boundary must be positive, got {alignment_boundary}")

    if transfer_length % alignment_boundary == 0:
        return transfer_length

    aligned = ((transfer_length // alignment_boundary) + 1) * alignment_boundary
    return aligned


def compute_padding_bytes(transfer_length, alignment_boundary):
    """
    Compute how many padding bytes are needed for alignment.

    Args:
        transfer_length: original byte count
        alignment_boundary: required alignment in bytes

    Returns:
        padding bytes needed (0 if already aligned)
    """
    if alignment_boundary <= 0:
        raise ValueError(f"Alignment boundary must be positive, got {alignment_boundary}")

    remainder = transfer_length % alignment_boundary
    if remainder == 0:
        return 0
    return alignment_boundary - remainder


def align_descriptor_transfers(descriptors, alignment_boundary):
    """
    Compute aligned transfer lengths for all descriptors in the chain.

    Args:
        descriptors: list of DMADescriptor objects
        alignment_boundary: alignment requirement in bytes

    Returns:
        list of dicts with:
          - descriptor_id
          - original_length
          - aligned_length
          - padding_bytes
          - alignment_ratio (aligned/original, measure of waste)
    """
    results = []
    for desc in descriptors:
        original = desc.transfer_length
        aligned = compute_aligned_length(original, alignment_boundary)
        padding = aligned - original
        ratio = aligned / original if original > 0 else 1.0

        results.append({
            "descriptor_id": desc.descriptor_id,
            "original_length": original,
            "aligned_length": aligned,
            "padding_bytes": padding,
            "alignment_ratio": ratio
        })

    return results


def compute_alignment_efficiency(alignment_results):
    """
    Compute overall alignment efficiency metrics for the chain.

    Args:
        alignment_results: output from align_descriptor_transfers

    Returns:
        dict with:
          - total_original_bytes: sum of original lengths
          - total_aligned_bytes: sum of aligned lengths
          - total_padding_bytes: total padding added
          - efficiency_percent: (original / aligned) * 100
          - max_waste_ratio: worst-case alignment ratio
    """
    if not alignment_results:
        return {
            "total_original_bytes": 0,
            "total_aligned_bytes": 0,
            "total_padding_bytes": 0,
            "efficiency_percent": 100.0,
            "max_waste_ratio": 1.0
        }

    total_original = sum(r["original_length"] for r in alignment_results)
    total_aligned = sum(r["aligned_length"] for r in alignment_results)
    total_padding = sum(r["padding_bytes"] for r in alignment_results)
    efficiency = (total_original / total_aligned * 100.0) if total_aligned > 0 else 100.0
    max_ratio = max(r["alignment_ratio"] for r in alignment_results)

    return {
        "total_original_bytes": total_original,
        "total_aligned_bytes": total_aligned,
        "total_padding_bytes": total_padding,
        "efficiency_percent": round(efficiency, 4),
        "max_waste_ratio": round(max_ratio, 6)
    }


def next_power_of_2(value):
    """
    Compute the next power of 2 >= value.

    Args:
        value: positive integer

    Returns:
        smallest power of 2 that is >= value
    """
    if value <= 0:
        raise ValueError(f"Value must be positive, got {value}")
    if value == 1:
        return 1
    return 1 << (value - 1).bit_length()


def validate_transfer_within_boundary(aligned_length, max_transfer_boundary):
    """
    Validate that a transfer length does not exceed the hardware maximum
    after power-of-2 rounding for internal buffer allocation.

    Args:
        aligned_length: the transfer length to validate
        max_transfer_boundary: maximum transfer the hardware supports

    Returns:
        dict with:
          - is_valid: whether transfer fits within boundary
          - rounded_size: power-of-2 rounded allocation size
          - exceeds_by: bytes over boundary (0 if valid)
    """
    rounded = next_power_of_2(aligned_length)

    return {
        "is_valid": rounded <= max_transfer_boundary,
        "rounded_size": rounded,
        "exceeds_by": max(0, rounded - max_transfer_boundary)
    }
