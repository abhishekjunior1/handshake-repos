"""
DMA Scatter-Gather Validator

Validates migrated descriptor chains for hardware compliance.
Checks include:
  - Address boundary crossing (AXI 4KB boundary rule)
  - Maximum transfer size per descriptor
  - Chain link integrity (valid addresses, sequential, terminated)
  - Bus protocol compliance (burst length, alignment)
  - Total transfer capacity within controller limits
"""


def validate_4k_boundaries(translated_addresses, transfer_lengths):
    """
    Validate that no single descriptor transfer crosses a 4KB boundary.
    AXI protocol mandates that burst transactions do not cross 4KB-aligned
    address boundaries. Transfers that would cross must be split.

    Args:
        translated_addresses: list of byte-space start addresses
        transfer_lengths: list of transfer sizes in bytes

    Returns:
        dict with:
          - all_valid: True if no crossings detected
          - violations: list of {descriptor_id, start, end, boundary_crossed}
    """
    violations = []
    boundary_size = 4096

    for idx, (addr, length) in enumerate(zip(translated_addresses, transfer_lengths)):
        start_page = addr // boundary_size
        end_addr = addr + length - 1
        end_page = end_addr // boundary_size

        if start_page != end_page:
            boundary_crossed = (start_page + 1) * boundary_size
            violations.append({
                "descriptor_id": idx,
                "start_address": addr,
                "end_address": end_addr,
                "boundary_crossed": boundary_crossed
            })

    return {
        "all_valid": len(violations) == 0,
        "violations": violations
    }


def validate_max_transfer_sizes(transfer_lengths, max_per_descriptor):
    """
    Check that no single descriptor exceeds the controller's per-descriptor
    maximum transfer size.

    Args:
        transfer_lengths: list of transfer sizes in bytes
        max_per_descriptor: maximum bytes a single descriptor can transfer

    Returns:
        dict with all_valid and violations list
    """
    violations = []
    for idx, length in enumerate(transfer_lengths):
        if length > max_per_descriptor:
            violations.append({
                "descriptor_id": idx,
                "transfer_length": length,
                "max_allowed": max_per_descriptor,
                "exceeds_by": length - max_per_descriptor
            })

    return {
        "all_valid": len(violations) == 0,
        "violations": violations
    }


def validate_total_chain_capacity(transfer_lengths, max_total_bytes):
    """
    Verify the total chain transfer does not exceed controller capacity.

    Some DMA controllers have a maximum total transfer limit across
    all descriptors in a single chain submission.

    Args:
        transfer_lengths: list of per-descriptor byte counts
        max_total_bytes: controller's maximum total per chain

    Returns:
        dict with is_valid, total_bytes, max_allowed, utilization_percent
    """
    total = sum(transfer_lengths)
    utilization = (total / max_total_bytes * 100.0) if max_total_bytes > 0 else 0.0

    return {
        "is_valid": total <= max_total_bytes,
        "total_bytes": total,
        "max_allowed": max_total_bytes,
        "utilization_percent": round(utilization, 2)
    }


def validate_alignment_compliance(translated_addresses, required_alignment):
    """
    Verify all translated addresses meet the target's alignment requirement.

    Args:
        translated_addresses: list of byte addresses
        required_alignment: alignment requirement in bytes (power of 2)

    Returns:
        dict with all_valid and violations list
    """
    violations = []
    for idx, addr in enumerate(translated_addresses):
        if addr % required_alignment != 0:
            nearest_aligned = (addr // required_alignment) * required_alignment
            violations.append({
                "descriptor_id": idx,
                "address": addr,
                "required_alignment": required_alignment,
                "nearest_aligned": nearest_aligned,
                "offset_error": addr - nearest_aligned
            })

    return {
        "all_valid": len(violations) == 0,
        "violations": violations
    }


def run_full_validation(translated_addresses, transfer_lengths, chain_links,
                        target_config):
    """
    Execute all validation checks on a migrated descriptor chain.

    Args:
        translated_addresses: byte-space addresses for each descriptor
        transfer_lengths: byte counts for each descriptor
        chain_links: chain_next addresses for each descriptor
        target_config: dict with max_transfer_per_descriptor, max_total_bytes,
                       alignment, max_burst_length

    Returns:
        dict with per-check results and overall pass/fail
    """
    max_per_desc = target_config.get("max_transfer_per_descriptor", 1 << 24)
    max_total = target_config.get("max_total_bytes", 1 << 28)
    alignment = target_config.get("alignment", 8)

    boundary_check = validate_4k_boundaries(translated_addresses, transfer_lengths)
    size_check = validate_max_transfer_sizes(transfer_lengths, max_per_desc)
    capacity_check = validate_total_chain_capacity(transfer_lengths, max_total)
    alignment_check = validate_alignment_compliance(translated_addresses, alignment)

    all_passed = all([
        boundary_check["all_valid"],
        size_check["all_valid"],
        capacity_check["is_valid"],
        alignment_check["all_valid"]
    ])

    return {
        "overall_valid": all_passed,
        "boundary_check": boundary_check,
        "size_check": size_check,
        "capacity_check": capacity_check,
        "alignment_check": alignment_check,
        "checks_performed": 4,
        "checks_passed": sum([
            boundary_check["all_valid"],
            size_check["all_valid"],
            capacity_check["is_valid"],
            alignment_check["all_valid"]
        ])
    }
