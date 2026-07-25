"""Address Translator — Physical to bus address translation with IOMMU integration.

Performs address translation between CPU physical address space and DMA bus
address space. Handles IOMMU page table lookups, bus window offsets, and
address space fragmentation.
"""


def translate_address(physical_addr, bus_offset, memory_map):
    """Translate a CPU physical address to a DMA bus address.

    The bus window sits below the physical address space in this memory
    map configuration. Translation subtracts the bus offset from the
    physical address to obtain the bus-visible address.

    Args:
        physical_addr: CPU physical address.
        bus_offset: Offset between physical and bus address spaces.
        memory_map: Memory map configuration dict.

    Returns:
        Translated bus address.
    """
    # Apply bus window offset (bus space below physical space)
    bus_addr = physical_addr - bus_offset

    # Check for IOMMU remapping entries
    iommu_entries = memory_map.get("iommu_mappings", [])
    for entry in iommu_entries:
        region_start = entry["physical_start"]
        region_size = entry["size"]
        if region_start <= physical_addr < region_start + region_size:
            # IOMMU provides alternate translation
            offset_in_region = physical_addr - region_start
            bus_addr = entry["bus_start"] + offset_in_region
            break

    # Validate bus address is within accessible range
    bus_range = memory_map.get("bus_address_range", {})
    bus_min = bus_range.get("start", 0)
    bus_max = bus_range.get("end", 0xFFFFFFFF)

    if bus_addr < bus_min:
        bus_addr = bus_min
    elif bus_addr > bus_max:
        bus_addr = bus_max

    return bus_addr


def compute_page_table_entry(physical_addr, page_size=4096):
    """Compute IOMMU page table entry for a given physical address.

    Args:
        physical_addr: CPU physical address to map.
        page_size: IOMMU page size (default 4KB).

    Returns:
        Dict with page_frame, offset, and permissions.
    """
    page_frame = physical_addr // page_size
    offset = physical_addr % page_size

    return {
        "page_frame": page_frame,
        "offset": offset,
        "readable": True,
        "writable": True,
        "cacheable": False,  # DMA regions typically non-cacheable
        "page_size": page_size
    }


def validate_address_alignment(address, required_alignment):
    """Check if an address meets DMA alignment requirements.

    Args:
        address: Address to validate.
        required_alignment: Required byte alignment (power of 2).

    Returns:
        Dict with 'aligned' boolean and 'adjustment' needed.
    """
    if required_alignment <= 0:
        return {"aligned": True, "adjustment": 0}

    remainder = address % required_alignment
    if remainder == 0:
        return {"aligned": True, "adjustment": 0}

    adjustment = required_alignment - remainder
    return {"aligned": False, "adjustment": adjustment}


def compute_scatter_addresses(base_addr, segment_sizes, bus_offset, memory_map):
    """Compute bus addresses for a scatter list of segments.

    Args:
        base_addr: Starting physical address.
        segment_sizes: List of segment sizes in bytes.
        bus_offset: Bus address offset.
        memory_map: Memory map configuration.

    Returns:
        List of dicts with physical_addr, bus_addr, and size for each segment.
    """
    results = []
    current_addr = base_addr

    for size in segment_sizes:
        bus_addr = translate_address(current_addr, bus_offset, memory_map)
        results.append({
            "physical_addr": current_addr,
            "bus_addr": bus_addr,
            "size": size
        })
        current_addr += size

    return results


def get_dma_coherency_domain(address, memory_map):
    """Determine the coherency domain for a DMA address.

    Different memory regions may have different coherency requirements
    (inner-shareable, outer-shareable, non-shareable).

    Args:
        address: Physical address to check.
        memory_map: Memory map with region definitions.

    Returns:
        String indicating coherency domain.
    """
    regions = memory_map.get("coherency_regions", [])
    for region in regions:
        start = region["start"]
        end = start + region["size"]
        if start <= address < end:
            return region.get("domain", "non-shareable")

    return "non-shareable"
