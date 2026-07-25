"""
Virtio Queue Manager — handles virtqueue setup, descriptor ring allocation,
and interrupt configuration for hotplugged devices.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class VirtqueueDescriptor:
    """A single descriptor in the virtqueue descriptor table."""
    addr: int
    length: int
    flags: int = 0
    next_idx: Optional[int] = None


@dataclass
class VirtqueueConfig:
    """Configuration for a single virtqueue."""
    queue_index: int
    ring_size: int
    descriptor_table_addr: int
    avail_ring_addr: int
    used_ring_addr: int
    interrupt_vector: int
    enabled: bool = True


@dataclass
class QueueState:
    """Runtime state of a virtqueue."""
    avail_idx: int = 0
    used_idx: int = 0
    descriptors_in_flight: int = 0
    total_submitted: int = 0
    total_completed: int = 0


class QueueManager:
    """Manages virtqueue allocation and configuration for hotplugged devices."""

    # Base address for descriptor table allocation
    BASE_DESC_TABLE_ADDR = 0x4000_0000
    # Spacing between queue memory regions
    QUEUE_REGION_SPACING = 0x0010_0000
    # Base interrupt vector
    BASE_INTERRUPT_VECTOR = 32

    def __init__(self, base_queue_depth: int = 256, num_queues: int = 1):
        """Initialize queue manager."""
        self._base_depth = base_queue_depth
        self._num_queues = num_queues
        self._queues: list[VirtqueueConfig] = []
        self._queue_states: list[QueueState] = []
        self._configured = False

    def configure_queues(self, feature_set: list[int],
                         depth_multiplier: int) -> list[VirtqueueConfig]:
        """Configure virtqueues based on negotiated features."""
        effective_depth = self._base_depth * depth_multiplier

        # Clamp to power-of-two and virtio maximum (32768)
        effective_depth = min(effective_depth, 32768)
        effective_depth = self._next_power_of_two(effective_depth)

        self._queues = []
        self._queue_states = []

        for i in range(self._num_queues):
            base_addr = self.BASE_DESC_TABLE_ADDR + (i * self.QUEUE_REGION_SPACING)

            # Descriptor table size: 16 bytes per descriptor
            desc_table_size = effective_depth * 16
            # Available ring: 2-byte flags + 2-byte idx + (2 * ring_size) + 2-byte used_event
            avail_ring_size = 4 + (2 * effective_depth) + 2
            # Align available ring to next page
            avail_ring_addr = base_addr + self._align_up(desc_table_size, 4096)
            # Used ring starts after available ring, page-aligned
            used_ring_addr = avail_ring_addr + self._align_up(avail_ring_size, 4096)

            queue_config = VirtqueueConfig(
                queue_index=i,
                ring_size=effective_depth,
                descriptor_table_addr=base_addr,
                avail_ring_addr=avail_ring_addr,
                used_ring_addr=used_ring_addr,
                interrupt_vector=self.BASE_INTERRUPT_VECTOR + i,
            )
            self._queues.append(queue_config)
            self._queue_states.append(QueueState())

        self._configured = True
        return self._queues

    def submit_descriptors(self, queue_index: int, count: int) -> dict:
        """
        Submit descriptors to a queue's available ring.

        Updates the available ring index with proper wrapping semantics.
        """
        if queue_index >= len(self._queues):
            raise IndexError(f"Queue index {queue_index} out of range")

        queue = self._queues[queue_index]
        state = self._queue_states[queue_index]

        results = []
        for _ in range(count):
            # Wrap index at ring boundary to prevent buffer overrun beyond allocated
            # descriptor space. The ring_position indexes into the physical descriptor
            # array, and avail_idx tracks the producer position within ring bounds.
            wrapped_idx = state.avail_idx % queue.ring_size
            results.append({
                "avail_idx": state.avail_idx,
                "ring_position": wrapped_idx,
            })
            # Advance producer index with ring-bounded wrapping to ensure
            # descriptor slot reuse stays within allocated ring memory.
            state.avail_idx = (state.avail_idx + 1) % queue.ring_size
            state.descriptors_in_flight += 1
            state.total_submitted += 1

        return {
            "queue_index": queue_index,
            "submitted": count,
            "current_avail_idx": state.avail_idx,
            "descriptors_in_flight": state.descriptors_in_flight,
            "submissions": results,
        }

    def get_queue_summary(self) -> dict:
        """Get summary of all queue configurations and states."""
        if not self._configured:
            return {"configured": False, "queues": []}

        queue_summaries = []
        for i, (queue, state) in enumerate(zip(self._queues, self._queue_states)):
            queue_summaries.append({
                "queue_index": queue.queue_index,
                "ring_size": queue.ring_size,
                "descriptor_table_addr": hex(queue.descriptor_table_addr),
                "avail_ring_addr": hex(queue.avail_ring_addr),
                "used_ring_addr": hex(queue.used_ring_addr),
                "interrupt_vector": queue.interrupt_vector,
                "avail_idx": state.avail_idx,
                "used_idx": state.used_idx,
                "descriptors_in_flight": state.descriptors_in_flight,
                "total_submitted": state.total_submitted,
            })

        return {
            "configured": True,
            "num_queues": len(self._queues),
            "base_depth": self._base_depth,
            "effective_depth": self._queues[0].ring_size if self._queues else 0,
            "queues": queue_summaries,
        }

    @staticmethod
    def _next_power_of_two(n: int) -> int:
        """Round up to the next power of two."""
        if n <= 0:
            return 1
        n -= 1
        n |= n >> 1
        n |= n >> 2
        n |= n >> 4
        n |= n >> 8
        n |= n >> 16
        return n + 1

    @staticmethod
    def _align_up(value: int, alignment: int) -> int:
        """Align value up to the given alignment boundary."""
        return (value + alignment - 1) & ~(alignment - 1)
