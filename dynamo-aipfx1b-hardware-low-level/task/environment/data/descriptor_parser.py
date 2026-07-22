"""
DMA Scatter-Gather Descriptor Parser

Parses descriptor chain definitions from configuration data, validates
chain linkage integrity, and produces structured descriptor objects for
downstream processing stages.

Each descriptor in a scatter-gather chain contains:
  - source_address: physical address of data buffer (word-addressed)
  - transfer_length: number of bytes to transfer from this buffer
  - control_flags: bitmask for transfer configuration (interrupt, last, etc.)
  - chain_next: pointer to next descriptor (0x0 = chain terminator)
"""

import math


class DMADescriptor:
    """Represents a single scatter-gather DMA descriptor."""

    def __init__(self, descriptor_id, source_address, transfer_length,
                 control_flags, chain_next, priority_level=0):
        self.descriptor_id = descriptor_id
        self.source_address = source_address
        self.transfer_length = transfer_length
        self.control_flags = control_flags
        self.chain_next = chain_next
        self.priority_level = priority_level
        self.metadata = {}

    def is_chain_terminator(self):
        """Check if this descriptor terminates the chain."""
        return self.chain_next == 0x0

    def has_interrupt_flag(self):
        """Check if completion interrupt is requested."""
        return bool(self.control_flags & 0x01)

    def has_last_flag(self):
        """Check if this is marked as last in chain."""
        return bool(self.control_flags & 0x02)

    def get_transfer_direction(self):
        """Extract transfer direction from control flags (bit 2)."""
        return "memory_to_peripheral" if (self.control_flags & 0x04) else "peripheral_to_memory"

    def get_channel_priority(self):
        """Return the descriptor's assigned channel priority."""
        return self.priority_level

    def to_dict(self):
        """Serialize descriptor to dictionary."""
        return {
            "descriptor_id": self.descriptor_id,
            "source_address": self.source_address,
            "transfer_length": self.transfer_length,
            "control_flags": self.control_flags,
            "chain_next": self.chain_next,
            "priority_level": self.priority_level,
            "direction": self.get_transfer_direction(),
            "is_terminator": self.is_chain_terminator(),
            "has_interrupt": self.has_interrupt_flag(),
            "metadata": self.metadata
        }


def parse_descriptor_chain(raw_descriptors, source_config):
    """
    Parse a list of raw descriptor definitions into DMADescriptor objects.

    Args:
        raw_descriptors: list of dict with descriptor field values
        source_config: source architecture configuration (bus_width, word_size, etc.)

    Returns:
        list of DMADescriptor objects in chain order
    """
    descriptors = []
    word_size = source_config.get("word_size", 4)

    for idx, raw in enumerate(raw_descriptors):
        src_addr = raw["source_address"]
        xfer_len = raw["transfer_length"]
        ctrl = raw.get("control_flags", 0x00)
        chain_next = raw.get("chain_next", 0x0)
        priority = raw.get("priority_level", 0)

        # Validate source address is word-aligned for source architecture
        if src_addr % word_size != 0:
            raise ValueError(
                f"Descriptor {idx}: source_address 0x{src_addr:08X} not "
                f"aligned to {word_size}-byte word boundary"
            )

        # Validate transfer length is positive and within 24-bit DMA counter limit
        max_transfer = (1 << 24) - 1  # 16,777,215 bytes
        if xfer_len <= 0 or xfer_len > max_transfer:
            raise ValueError(
                f"Descriptor {idx}: transfer_length {xfer_len} out of range [1, {max_transfer}]"
            )

        descriptor = DMADescriptor(
            descriptor_id=idx,
            source_address=src_addr,
            transfer_length=xfer_len,
            control_flags=ctrl,
            chain_next=chain_next,
            priority_level=priority
        )

        # Attach raw metadata for traceability
        descriptor.metadata = {
            "original_word_address": src_addr // word_size,
            "word_size": word_size,
            "raw_index": idx
        }

        descriptors.append(descriptor)

    # Validate chain linkage consistency
    _validate_chain_linkage(descriptors)

    return descriptors


def _validate_chain_linkage(descriptors):
    """
    Verify that chain_next pointers form a valid linear chain.
    The last descriptor must be a terminator (chain_next == 0x0).
    """
    if not descriptors:
        return

    # Check that exactly one descriptor is a terminator
    terminators = [d for d in descriptors if d.is_chain_terminator()]
    if len(terminators) != 1:
        raise ValueError(
            f"Chain must have exactly one terminator, found {len(terminators)}"
        )

    # Terminator must be the last descriptor in the list
    if not descriptors[-1].is_chain_terminator():
        raise ValueError("Chain terminator must be the last descriptor in sequence")


def compute_chain_statistics(descriptors):
    """
    Compute aggregate statistics for a parsed descriptor chain.

    Returns dict with:
      - total_transfer_bytes: sum of all transfer lengths
      - descriptor_count: number of descriptors in chain
      - max_single_transfer: largest individual transfer
      - min_single_transfer: smallest individual transfer
      - has_priority_mix: whether multiple priority levels exist
      - direction_counts: count of each transfer direction
    """
    if not descriptors:
        return {
            "total_transfer_bytes": 0,
            "descriptor_count": 0,
            "max_single_transfer": 0,
            "min_single_transfer": 0,
            "has_priority_mix": False,
            "direction_counts": {}
        }

    lengths = [d.transfer_length for d in descriptors]
    priorities = set(d.priority_level for d in descriptors)
    directions = {}
    for d in descriptors:
        direction = d.get_transfer_direction()
        directions[direction] = directions.get(direction, 0) + 1

    return {
        "total_transfer_bytes": sum(lengths),
        "descriptor_count": len(descriptors),
        "max_single_transfer": max(lengths),
        "min_single_transfer": min(lengths),
        "has_priority_mix": len(priorities) > 1,
        "direction_counts": directions
    }
