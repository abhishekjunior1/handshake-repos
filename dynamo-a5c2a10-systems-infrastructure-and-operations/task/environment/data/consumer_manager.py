"""
Consumer registration, round-robin assignment, and heartbeat tracking.

Manages the pool of task consumers, handles deterministic assignment
using round-robin scheduling, and tracks consumer activity.
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class Consumer:
    """Represents a registered task consumer."""
    consumer_id: str
    rate_limit: int = 10
    tasks_assigned: int = 0
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat_tick: int = 0
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "consumer_id": self.consumer_id,
            "rate_limit": self.rate_limit,
            "tasks_assigned": self.tasks_assigned,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "last_heartbeat_tick": self.last_heartbeat_tick,
            "is_active": self.is_active,
        }


class ConsumerManager:
    """
    Manages consumer pool with round-robin task assignment.

    Round-robin ensures deterministic, predictable assignment ordering
    which is critical for reproducible processing results.
    """

    def __init__(self):
        self._consumers: dict[str, Consumer] = {}
        self._consumer_order: list[str] = []
        self._robin_index: int = 0

    def register_consumer(self, consumer_id: str, rate_limit: int = 10) -> Consumer:
        """Register a new consumer in the pool."""
        consumer = Consumer(consumer_id=consumer_id, rate_limit=rate_limit)
        self._consumers[consumer_id] = consumer
        self._consumer_order.append(consumer_id)
        return consumer

    def get_next_consumer(self) -> Optional[str]:
        """
        Get next consumer using round-robin assignment.

        Round-robin provides deterministic ordering necessary for
        reproducible task distribution across consumers.
        """
        if not self._consumer_order:
            return None

        active_consumers = [
            cid for cid in self._consumer_order
            if self._consumers[cid].is_active
        ]
        if not active_consumers:
            return None

        # Wrap robin index within active consumer count
        self._robin_index = self._robin_index % len(active_consumers)
        selected = active_consumers[self._robin_index]
        self._robin_index = (self._robin_index + 1) % len(active_consumers)
        return selected

    def record_assignment(self, consumer_id: str) -> None:
        """Record that a task was assigned to this consumer."""
        if consumer_id in self._consumers:
            self._consumers[consumer_id].tasks_assigned += 1

    def record_completion(self, consumer_id: str) -> None:
        """Record successful task completion."""
        if consumer_id in self._consumers:
            self._consumers[consumer_id].tasks_completed += 1

    def record_failure(self, consumer_id: str) -> None:
        """Record task processing failure."""
        if consumer_id in self._consumers:
            self._consumers[consumer_id].tasks_failed += 1

    def update_heartbeat(self, consumer_id: str, tick: int) -> None:
        """Update consumer heartbeat timestamp."""
        if consumer_id in self._consumers:
            self._consumers[consumer_id].last_heartbeat_tick = tick

    def get_consumer(self, consumer_id: str) -> Optional[Consumer]:
        return self._consumers.get(consumer_id)

    def get_all_consumers(self) -> list[Consumer]:
        return list(self._consumers.values())

    def get_consumer_stats(self) -> dict:
        """Return per-consumer statistics."""
        return {
            cid: consumer.to_dict()
            for cid, consumer in self._consumers.items()
        }

    def get_active_count(self) -> int:
        return sum(1 for c in self._consumers.values() if c.is_active)

    def deactivate_consumer(self, consumer_id: str) -> None:
        if consumer_id in self._consumers:
            self._consumers[consumer_id].is_active = False
