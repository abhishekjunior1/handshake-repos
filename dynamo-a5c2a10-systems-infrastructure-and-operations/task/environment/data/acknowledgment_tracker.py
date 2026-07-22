"""
Acknowledgment tracking with timeout detection and redelivery.

Tracks task processing acknowledgments from consumers, detects timeouts
for unacknowledged tasks, and manages the redelivery queue for timed-out tasks.
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AckRecord:
    """Tracks acknowledgment state for a dispatched task."""
    task_id: str
    consumer_id: str
    dispatched_at_tick: int
    timeout_ticks: int = 5
    acknowledged: bool = False
    ack_tick: Optional[int] = None
    nacked: bool = False
    nack_reason: Optional[str] = None

    def is_timed_out(self, current_tick: int) -> bool:
        """Check if this task has exceeded its ack timeout."""
        if self.acknowledged or self.nacked:
            return False
        return (current_tick - self.dispatched_at_tick) >= self.timeout_ticks


class AcknowledgmentTracker:
    """
    Manages task acknowledgment lifecycle.

    Tracks dispatched tasks, processes ack/nack signals from consumers,
    detects timeouts, and queues timed-out tasks for redelivery.
    """

    def __init__(self, default_timeout: int = 5):
        self._pending_acks: dict[str, AckRecord] = {}
        self._completed_acks: list[AckRecord] = []
        self._redelivery_queue: list[str] = []
        self._default_timeout = default_timeout
        self._total_acks = 0
        self._total_nacks = 0
        self._total_timeouts = 0

    def register_dispatch(self, task_id: str, consumer_id: str, tick: int,
                          timeout: Optional[int] = None) -> None:
        """Register a task dispatch for ack tracking."""
        record = AckRecord(
            task_id=task_id,
            consumer_id=consumer_id,
            dispatched_at_tick=tick,
            timeout_ticks=timeout or self._default_timeout,
        )
        self._pending_acks[task_id] = record

    def acknowledge(self, task_id: str, tick: int) -> bool:
        """Process a positive acknowledgment for a task."""
        if task_id not in self._pending_acks:
            return False
        record = self._pending_acks[task_id]
        record.acknowledged = True
        record.ack_tick = tick
        self._total_acks += 1
        self._completed_acks.append(record)
        del self._pending_acks[task_id]
        return True

    def negative_acknowledge(self, task_id: str, reason: str, tick: int) -> bool:
        """Process a negative acknowledgment (task failed)."""
        if task_id not in self._pending_acks:
            return False
        record = self._pending_acks[task_id]
        record.nacked = True
        record.nack_reason = reason
        record.ack_tick = tick
        self._total_nacks += 1
        self._completed_acks.append(record)
        del self._pending_acks[task_id]
        return True

    def check_timeouts(self, current_tick: int) -> list[str]:
        """Check for timed-out tasks and queue them for redelivery."""
        timed_out = []
        for task_id, record in list(self._pending_acks.items()):
            if record.is_timed_out(current_tick):
                timed_out.append(task_id)
                self._redelivery_queue.append(task_id)
                self._total_timeouts += 1
                del self._pending_acks[task_id]
        return timed_out

    def get_redelivery_queue(self) -> list[str]:
        """Return and clear the redelivery queue."""
        queue = list(self._redelivery_queue)
        self._redelivery_queue.clear()
        return queue

    def has_pending(self) -> bool:
        return len(self._pending_acks) > 0

    def get_pending_count(self) -> int:
        return len(self._pending_acks)

    def get_stats(self) -> dict:
        return {
            "total_acks": self._total_acks,
            "total_nacks": self._total_nacks,
            "total_timeouts": self._total_timeouts,
            "pending_count": len(self._pending_acks),
            "redelivery_queue_size": len(self._redelivery_queue),
        }

    def get_completed_records(self) -> list[dict]:
        return [
            {
                "task_id": r.task_id,
                "consumer_id": r.consumer_id,
                "dispatched_at_tick": r.dispatched_at_tick,
                "ack_tick": r.ack_tick,
                "acknowledged": r.acknowledged,
                "nacked": r.nacked,
                "nack_reason": r.nack_reason,
            }
            for r in self._completed_acks
        ]
