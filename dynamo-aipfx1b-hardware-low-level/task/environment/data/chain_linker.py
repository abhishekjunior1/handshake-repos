"""
DMA Scatter-Gather Chain Linker

Rebuilds descriptor chain linkage for the target architecture.
Each descriptor's chain_next pointer must be recomputed based on:
  - Target base address where descriptors will be stored
  - Target descriptor size (includes all fields + metadata overhead)
  - Sequential ordering within the chain

The chain_next pointer for descriptor N points to the physical address
of descriptor N+1 in the target descriptor table. The last descriptor's
chain_next is set to the null terminator (0x0).
"""


def compute_descriptor_size(data_fields_size, metadata_overhead):
    """
    Compute total descriptor storage size for the target architecture.

    Target architecture descriptors include a fixed metadata header
    that stores housekeeping information (status flags, channel ID,
    completion token). This overhead is added to the data field size.

    Args:
        data_fields_size: size of the descriptor's data fields in bytes
        metadata_overhead: fixed metadata header size in bytes

    Returns:
        total descriptor size in bytes
    """
    return data_fields_size + metadata_overhead


def link_descriptors(descriptor_count, base_address, descriptor_size):
    """
    Generate chain_next addresses for a linear descriptor chain.

    Each descriptor's next pointer is computed as:
        base_address + (index + 1) * descriptor_size

    The last descriptor gets chain_next = 0x0 (null terminator).

    Args:
        descriptor_count: number of descriptors in the chain
        base_address: physical start address of the descriptor table
        descriptor_size: size of each descriptor in bytes (including metadata)

    Returns:
        list of chain_next addresses (length == descriptor_count)
    """
    if descriptor_count <= 0:
        return []

    chain_links = []
    for idx in range(descriptor_count):
        if idx == descriptor_count - 1:
            # Last descriptor terminates the chain
            chain_links.append(0x0)
        else:
            # Next descriptor starts at base + (idx+1) * size
            next_addr = base_address + (idx + 1) * descriptor_size
            chain_links.append(next_addr)

    return chain_links


def compute_descriptor_table_layout(descriptor_count, base_address, descriptor_size):
    """
    Compute the full memory layout of the descriptor table.

    Returns the start address of each descriptor in the table,
    useful for debugging and verification.

    Args:
        descriptor_count: number of descriptors
        base_address: start of descriptor table
        descriptor_size: per-descriptor size

    Returns:
        list of dicts with descriptor_index, start_address, end_address
    """
    layout = []
    for idx in range(descriptor_count):
        start = base_address + idx * descriptor_size
        end = start + descriptor_size - 1
        layout.append({
            "descriptor_index": idx,
            "start_address": start,
            "end_address": end
        })
    return layout


def validate_chain_links(chain_links, base_address, descriptor_size, descriptor_count):
    """
    Validate that chain linkage is self-consistent.

    Checks:
      - Each non-terminal link points to a valid descriptor address
      - Last link is null terminator
      - No circular references

    Args:
        chain_links: list of chain_next addresses
        base_address: table start address
        descriptor_size: per-descriptor size
        descriptor_count: total descriptors

    Returns:
        dict with is_valid (bool) and errors (list of strings)
    """
    errors = []

    if len(chain_links) != descriptor_count:
        errors.append(
            f"Chain link count {len(chain_links)} != descriptor count {descriptor_count}"
        )
        return {"is_valid": False, "errors": errors}

    # Last must be terminator
    if chain_links[-1] != 0x0:
        errors.append(f"Last chain_next is 0x{chain_links[-1]:08X}, expected 0x0")

    # Each non-terminal link must point to a valid descriptor slot
    valid_addresses = set()
    for idx in range(descriptor_count):
        valid_addresses.add(base_address + idx * descriptor_size)

    for idx in range(descriptor_count - 1):
        link = chain_links[idx]
        if link not in valid_addresses:
            errors.append(
                f"Descriptor {idx}: chain_next 0x{link:08X} not a valid descriptor address"
            )

    # Check sequential ordering (no out-of-order links)
    for idx in range(descriptor_count - 1):
        expected = base_address + (idx + 1) * descriptor_size
        if chain_links[idx] != expected:
            errors.append(
                f"Descriptor {idx}: chain_next 0x{chain_links[idx]:08X} "
                f"!= expected 0x{expected:08X} (non-sequential)"
            )

    return {"is_valid": len(errors) == 0, "errors": errors}


def compute_table_footprint(descriptor_count, descriptor_size):
    """
    Compute total memory footprint of the descriptor table.

    Args:
        descriptor_count: number of descriptors
        descriptor_size: per-descriptor size in bytes

    Returns:
        total bytes occupied by the descriptor table
    """
    return descriptor_count * descriptor_size
