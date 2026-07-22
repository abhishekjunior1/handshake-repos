"""
DMA Address Translator

Converts word-addressed source descriptors to byte-addressed target
descriptors with bus width scaling and address space remapping.
"""


def translate_address(word_address, bus_width_bytes):
    """
    Convert a word-aligned address to a byte address using the given
    bus width as the scaling factor.

    Args:
        word_address: source address in word units
        bus_width_bytes: bus width in bytes for address scaling

    Returns:
        byte_address: translated address in byte-addressable space
    """
    byte_address = word_address * bus_width_bytes
    return byte_address


def translate_descriptor_addresses(descriptors, bus_width_bytes, address_offset=0):
    """
    Translate all descriptor source addresses from word-space to byte-space.

    Applies uniform bus width scaling plus an optional base offset for
    memory-mapped region remapping.

    Args:
        descriptors: list of DMADescriptor objects
        bus_width_bytes: bus width for address scaling
        address_offset: optional base offset added after scaling

    Returns:
        list of translated addresses (preserves input ordering)
    """
    translated = []
    for desc in descriptors:
        byte_addr = translate_address(desc.source_address, bus_width_bytes)
        final_addr = byte_addr + address_offset
        translated.append(final_addr)
    return translated


def compute_address_span(translated_addresses, transfer_lengths):
    """
    Compute the total address span covered by the descriptor chain.

    Used for validating that the migrated chain fits within the target
    controller's addressable range.

    Args:
        translated_addresses: list of byte addresses
        transfer_lengths: corresponding transfer lengths in bytes

    Returns:
        dict with min_address, max_address, total_span
    """
    if not translated_addresses:
        return {"min_address": 0, "max_address": 0, "total_span": 0}

    min_addr = min(translated_addresses)
    max_addr = max(
        addr + length
        for addr, length in zip(translated_addresses, transfer_lengths)
    )

    return {
        "min_address": min_addr,
        "max_address": max_addr,
        "total_span": max_addr - min_addr
    }


def validate_address_alignment(address, required_alignment):
    """
    Check if an address meets an alignment requirement.

    Args:
        address: byte address to validate
        required_alignment: required alignment in bytes (must be power of 2)

    Returns:
        bool: True if address is properly aligned
    """
    if required_alignment <= 0:
        raise ValueError("Alignment must be positive")
    if required_alignment & (required_alignment - 1) != 0:
        raise ValueError(f"Alignment {required_alignment} must be a power of 2")
    return (address % required_alignment) == 0


def compute_alignment_padding(address, required_alignment):
    """
    Compute padding needed to reach next aligned address.

    Args:
        address: current byte address
        required_alignment: target alignment in bytes

    Returns:
        padding_bytes: number of bytes to add for alignment (0 if already aligned)
    """
    if required_alignment <= 1:
        return 0
    remainder = address % required_alignment
    if remainder == 0:
        return 0
    return required_alignment - remainder


def build_address_map(descriptors, bus_width_bytes, address_offset=0):
    """
    Build a complete address translation map for the descriptor chain.

    Returns a list of dicts, each containing:
      - descriptor_id: original descriptor index
      - original_address: word-space address from source
      - translated_address: byte-space address
      - alignment_valid: whether translated address meets default 8-byte alignment
    """
    default_alignment = 8

    address_map = []
    for desc in descriptors:
        translated = translate_address(desc.source_address, bus_width_bytes)
        final = translated + address_offset

        address_map.append({
            "descriptor_id": desc.descriptor_id,
            "original_address": desc.source_address,
            "translated_address": final,
            "alignment_valid": validate_address_alignment(final, default_alignment)
        })

    return address_map
