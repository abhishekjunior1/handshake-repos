"""
Retry handler with exponential backoff and dead letter queue routing.

Manages retry decisions for failed tasks, calculates backoff delays,
and routes exhausted tasks to the dead letter queue.
"""

from typing import Optional
from dataclasses import dataclass, field


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    base_backoff_ms: int = 100
    backoff_multiplier: float = 2.0
    max_backoff_ms: int = 10000


@dataclass
class DeadLetterEntry:
    """A task that has exhausted all retry attempts."""
    task_id: str
    final_retry_count: int
    failure_reason: str
    routed_at_tick: int
    original_priority: int
    payload: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "final_retry_count": self.final_retry_count,
            "failure_reason": self.failure_reason,
            "routed_at_tick": self.routed_at_tick,
            "original_priority": self.original_priority,
        }


class RetryHandler:
    """
    Handles retry decisions and dead letter queue management.

    Determines whether a failed task should be retried or sent to DLQ
    based on the configured retry policy and current retry count.
    """

    def __init__(self, policy: Optional[RetryPolicy] = None):
        self._policy = policy or RetryPolicy()
        self._dead_letter_queue: list[DeadLetterEntry] = []
        self._retry_history: dict[str, list] = {}

    @property
    def policy(self) -> RetryPolicy:
        return self._policy

    def should_retry(self, task_id: str, current_retry_count: int) -> bool:
        """
        Determine if a task should be retried based on its current retry count.
        Returns True if retry_count has not exceeded max_retries.
        """
        return current_retry_count < self._policy.max_retries

    def calculate_backoff(self, retry_count: int) -> int:
        """
        Calculate exponential backoff delay for the given retry attempt.
        Uses: base * (multiplier ^ retry_count), capped at max_backoff.
        """
        delay = self._policy.base_backoff_ms * (
            self._policy.backoff_multiplier ** retry_count
        )
        return int(min(delay, self._policy.max_backoff_ms))

    def record_retry(self, task_id: str, retry_count: int, tick: int) -> None:
        """Record a retry attempt for tracking purposes."""
        if task_id not in self._retry_history:
            self._retry_history[task_id] = []
        self._retry_history[task_id].append({
            "retry_number": retry_count,
            "tick": tick,
            "backoff_ms": self.calculate_backoff(retry_count),
        })

    def route_to_dlq(self, task_id: str, retry_count: int, reason: str,
                     tick: int, priority: int, payload: dict = None) -> DeadLetterEntry:
        """Route a failed task to the dead letter queue."""
        entry = DeadLetterEntry(
            task_id=task_id,
            final_retry_count=retry_count,
            failure_reason=reason,
            routed_at_tick=tick,
            original_priority=priority,
            payload=payload or {},
        )
        self._dead_letter_queue.append(entry)
        return entry

    def get_dlq_contents(self) -> list[dict]:
        """Return all dead letter queue entries as dicts."""
        return [entry.to_dict() for entry in self._dead_letter_queue]

    def get_dlq_size(self) -> int:
        return len(self._dead_letter_queue)

    def get_retry_history(self, task_id: str) -> list:
        return self._retry_history.get(task_id, [])

    def get_full_history(self) -> dict:
        return dict(self._retry_history)

    def is_in_dlq(self, task_id: str) -> bool:
        """Check if a task has been routed to the dead letter queue."""
        return any(e.task_id == task_id for e in self._dead_letter_queue)

    def get_stats(self) -> dict:
        return {
            "dlq_size": len(self._dead_letter_queue),
            "tasks_retried": len(self._retry_history),
            "total_retry_attempts": sum(
                len(h) for h in self._retry_history.values()
            ),
            "policy": {
                "max_retries": self._policy.max_retries,
                "base_backoff_ms": self._policy.base_backoff_ms,
                "backoff_multiplier": self._policy.backoff_multiplier,
            }
        }
