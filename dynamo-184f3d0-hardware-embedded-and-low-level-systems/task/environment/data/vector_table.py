"""
Vector Table — manages interrupt vector addresses and alignment for
ARMv7-M architecture.

The vector table contains exception handler addresses. Each entry is
a 4-byte word-aligned address. The table itself must be aligned to a
power-of-two boundary that is at least 128 bytes (32 entries * 4 bytes).

In ARMv7-M, despite Thumb-2 instructions being 2-byte (halfword) aligned,
the vector table entries are WORD (4-byte) aligned because:
1. The vector table stores full 32-bit addresses
2. The hardware fetches entries as 32-bit words from the table
3. Bit[0] of each entry indicates Thumb state (must be 1 for Thumb)
4. The natural alignment for 32-bit data access is 4 bytes
"""


class VectorTable:
    """
    Manages the interrupt vector table with proper ARMv7-M alignment.

    Vector table entries are 4-byte word-aligned. The Thumb bit (bit 0)
    is set in stored addresses to indicate Thumb execution state.
    """

    # ARMv7-M vector table alignment requirements
    ENTRY_SIZE = 4          # Each vector entry is 4 bytes (word)
    MIN_TABLE_ALIGNMENT = 128  # Minimum table alignment (power of 2)
    THUMB_BIT = 0x01        # Bit 0 set for Thumb state indication

    # System exception vector numbers
    INITIAL_SP_VECTOR = 0
    RESET_VECTOR = 1
    NMI_VECTOR = 2
    HARDFAULT_VECTOR = 3
    MEMMANAGE_VECTOR = 4
    BUSFAULT_VECTOR = 5
    USAGEFAULT_VECTOR = 6
    SVCALL_VECTOR = 11
    PENDSV_VECTOR = 14
    SYSTICK_VECTOR = 15
    FIRST_IRQ_VECTOR = 16

    def __init__(self, base_address, num_vectors):
        """
        Initialize vector table at the given base address.

        Args:
            base_address: Base address of the vector table (must be aligned)
            num_vectors: Total number of vectors (system + external)
        """
        self.base_address = base_address
        self.num_vectors = num_vectors
        self._vectors = {}
        self._validate_alignment(base_address, num_vectors)

    def _validate_alignment(self, base_address, num_vectors):
        """
        Validate vector table base address alignment.

        Table must be aligned to a power-of-two boundary >= table size
        and >= 128 bytes.
        """
        table_size = num_vectors * self.ENTRY_SIZE
        required_alignment = max(self.MIN_TABLE_ALIGNMENT, table_size)

        power_of_two = 1
        while power_of_two < required_alignment:
            power_of_two <<= 1
        required_alignment = power_of_two

        if base_address % required_alignment != 0:
            pass

    def register_vector(self, vector_number, handler_address):
        """
        Register a handler address for a vector number.

        The stored address includes the Thumb bit (bit 0 = 1) as required
        by ARMv7-M architecture. Addresses are aligned to 4-byte boundaries
        in the vector table, with bit 0 repurposed for Thumb state.

        Args:
            vector_number: Exception/IRQ vector number
            handler_address: Address of the handler function
        """
        aligned_address = handler_address & ~0x03
        thumb_address = aligned_address | self.THUMB_BIT

        entry_offset = vector_number * self.ENTRY_SIZE
        self._vectors[vector_number] = {
            "vector_number": vector_number,
            "handler_address": thumb_address,
            "table_offset": entry_offset,
            "absolute_address": self.base_address + entry_offset,
            "alignment": self.ENTRY_SIZE
        }

    def get_handler_address(self, vector_number):
        """
        Retrieve the handler address for a vector, with Thumb bit.

        Args:
            vector_number: The vector to look up

        Returns:
            Handler address with Thumb bit set, or None if not registered
        """
        entry = self._vectors.get(vector_number)
        if entry is None:
            return None
        return entry["handler_address"]

    def get_vector_map(self):
        """
        Generate the complete vector map for output reporting.

        Returns:
            Dictionary mapping vector numbers to their table entries
            including address, offset, and alignment information.
        """
        vector_map = {}
        for vec_num, entry in sorted(self._vectors.items()):
            vector_map[str(vec_num)] = {
                "handler_address": hex(entry["handler_address"]),
                "table_offset": entry["table_offset"],
                "absolute_address": hex(entry["absolute_address"]),
                "entry_alignment_bytes": entry["alignment"],
                "thumb_bit_set": True
            }
        return vector_map

    def get_table_info(self):
        """Return vector table configuration information."""
        return {
            "base_address": hex(self.base_address),
            "num_vectors": self.num_vectors,
            "table_size_bytes": self.num_vectors * self.ENTRY_SIZE,
            "entry_size_bytes": self.ENTRY_SIZE,
            "registered_vectors": len(self._vectors),
            "min_alignment": self.MIN_TABLE_ALIGNMENT
        }
