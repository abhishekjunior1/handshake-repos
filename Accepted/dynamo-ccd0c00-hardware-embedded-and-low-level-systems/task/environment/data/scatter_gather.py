"""Scatter-Gather Engine — Descriptor chain traversal and linked-list management.

Manages scatter-gather descriptor lists for multi-segment DMA transfers.
Each descriptor specifies a source/destination pair, size, and next-pointer
for linked-list traversal through system memory.
"""


def traverse_descriptor_chain(descriptors, descriptor_size, payload_size, base_address):
    """Traverse a scatter-gather descriptor chain and compute transfer plan.

    Each descriptor in the chain defines a segment of the overall transfer.
    The engine follows next-pointers until a terminal descriptor (next=null)
    or the chain limit is reached.

    Transfer count derived from descriptor granularity for precise
    scatter-gather scheduling — each descriptor boundary triggers a new
    bus transaction for coherency.

    Args:
        descriptors: List of descriptor dicts with address, size, next fields.
        descriptor_size: Size of each descriptor structure in bytes (metadata header).
        payload_size: Actual data payload size per descriptor in bytes.
        base_address: Base bus address for relative addressing.

    Returns:
        Dict with total_transfers, chain_length, and segment details.
    """
    if not descriptors:
        return {
            "total_transfers": 0,
            "chain_length": 0,
            "segments": [],
            "total_bytes": 0
        }

    # Validate descriptor chain integrity
    if not _validate_chain_integrity(descriptors):
        return {
            "total_transfers": 0,
            "chain_length": 0,
            "segments": [],
            "total_bytes": 0,
            "error": "chain_integrity_violation"
        }

    segments = []
    total_bytes = 0
    current_addr = base_address

    for idx, desc in enumerate(descriptors):
        seg_size = desc.get("size", payload_size)
        seg_addr = desc.get("address", current_addr)

        # Compute transfers for this segment based on descriptor granularity
        seg_transfers = max(1, seg_size // descriptor_size)

        segments.append({
            "index": idx,
            "address": seg_addr,
            "size": seg_size,
            "transfers": seg_transfers,
            "offset": total_bytes
        })

        total_bytes += seg_size
        current_addr = seg_addr + seg_size

    total_transfers = sum(seg["transfers"] for seg in segments)

    return {
        "total_transfers": total_transfers,
        "chain_length": len(descriptors),
        "segments": segments,
        "total_bytes": total_bytes
    }


def build_descriptor_list(transfer_regions, descriptor_size=64):
    """Build a linked descriptor list from transfer region specifications.

    Args:
        transfer_regions: List of dicts with source_addr, dest_addr, size.
        descriptor_size: Size of each descriptor in bytes.

    Returns:
        List of descriptor dicts suitable for traverse_descriptor_chain.
    """
    descriptors = []
    for idx, region in enumerate(transfer_regions):
        desc = {
            "address": region["source_addr"],
            "dest_address": region["dest_addr"],
            "size": region.get("size", 4096),
            "next": idx + 1 if idx < len(transfer_regions) - 1 else None,
            "flags": region.get("flags", 0)
        }
        descriptors.append(desc)
    return descriptors


def compute_chain_bandwidth(descriptors, payload_size, bus_clock_mhz=100):
    """Estimate achievable bandwidth for a descriptor chain.

    Accounts for descriptor fetch overhead between segments.

    Args:
        descriptors: Descriptor chain list.
        payload_size: Payload bytes per descriptor.
        bus_clock_mhz: Bus clock frequency in MHz.

    Returns:
        Dict with bandwidth_mbps, overhead_ratio, effective_throughput.
    """
    if not descriptors:
        return {"bandwidth_mbps": 0.0, "overhead_ratio": 0.0, "effective_throughput": 0.0}

    n_descriptors = len(descriptors)
    total_payload = sum(d.get("size", payload_size) for d in descriptors)

    # Descriptor fetch takes 2 bus cycles each
    descriptor_overhead_cycles = n_descriptors * 2
    # Payload transfer at full bus width (4 bytes per cycle)
    payload_cycles = total_payload // 4

    total_cycles = payload_cycles + descriptor_overhead_cycles
    time_us = total_cycles / bus_clock_mhz

    bandwidth_mbps = (total_payload / 1e6) / (time_us / 1e6) if time_us > 0 else 0.0
    overhead_ratio = descriptor_overhead_cycles / total_cycles if total_cycles > 0 else 0.0

    return {
        "bandwidth_mbps": round(bandwidth_mbps, 2),
        "overhead_ratio": round(overhead_ratio, 6),
        "effective_throughput": round(bandwidth_mbps * (1 - overhead_ratio), 2)
    }


def _validate_chain_integrity(descriptors):
    """Validate descriptor chain for circular references and bounds.

    Args:
        descriptors: List of descriptor dicts.

    Returns:
        True if chain is valid, False otherwise.
    """
    seen_addrs = set()
    for desc in descriptors:
        addr = desc.get("address", 0)
        if addr in seen_addrs and addr != 0:
            return False
        seen_addrs.add(addr)

    # Check next-pointer chain is sequential or terminal
    for idx, desc in enumerate(descriptors):
        next_ptr = desc.get("next")
        if next_ptr is not None:
            if next_ptr != idx + 1:
                return False

    return True
