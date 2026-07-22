"""
Priority queue implementation for the distributed task scheduler.

Supports multi-level priority buckets with FIFO ordering within each level.
Tasks are dequeued from the highest priority bucket first.
"""

import heapq
from dataclasses import dataclass, field
from typing import Any, Optional
from collections import deque


@dataclass(order=True)
class TaskEntry:
    """Represents a task in the priority queue system."""
    priority: int
    sequence_num: int = field(compare=True)
    task_id: str = field(compare=False)
    payload: dict = field(compare=False, default_factory=dict)
    retry_count: int = field(compare=False, default=0)
    max_retries: int = field(compare=False, default=0)
    status: str = field(compare=False, default="pending")
    assigned_consumer: Optional[str] = field(compare=False, default=None)
    created_at: int = field(compare=False, default=0)
    failure_schedule: list = field(compare=False, default_factory=list)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "priority": self.priority,
            "payload": self.payload,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "status": self.status,
            "assigned_consumer": self.assigned_consumer,
            "created_at": self.created_at,
            "failure_schedule": self.failure_schedule,
        }


class PriorityTaskQueue:
    """
    Multi-level priority queue with FIFO ordering within each priority level.

    Priority levels: 1 (highest) to 10 (lowest).
    Within the same priority, tasks are served in insertion order.
    """

    def __init__(self):
        self._buckets: dict[int, deque] = {}
        self._sequence_counter: int = 0
        self._size: int = 0
        self._priority_levels = list(range(1, 11))

    @property
    def size(self) -> int:
        return self._size

    def is_empty(self) -> bool:
        return self._size == 0

    def enqueue(self, task: TaskEntry) -> None:
        """Add a task to the appropriate priority bucket at the back."""
        priority = task.priority
        if priority not in self._buckets:
            self._buckets[priority] = deque()
        task.sequence_num = self._sequence_counter
        self._sequence_counter += 1
        self._buckets[priority].append(task)
        self._size += 1

    def dequeue(self) -> Optional[TaskEntry]:
        """Remove and return the highest-priority task (lowest number = highest priority)."""
        for priority in sorted(self._buckets.keys()):
            bucket = self._buckets[priority]
            if bucket:
                self._size -= 1
                task = bucket.popleft()
                task.status = "dequeued"
                return task
        return None

    def peek(self) -> Optional[TaskEntry]:
        """Look at the highest-priority task without removing it."""
        for priority in sorted(self._buckets.keys()):
            bucket = self._buckets[priority]
            if bucket:
                return bucket[0]
        return None

    def requeue(self, task: TaskEntry) -> None:
        """Re-insert a task at the back of its priority bucket."""
        task.status = "requeued"
        task.assigned_consumer = None
        if task.priority not in self._buckets:
            self._buckets[task.priority] = deque()
        task.sequence_num = self._sequence_counter
        self._sequence_counter += 1
        self._buckets[task.priority].append(task)
        self._size += 1

    def requeue_at_back(self, task: TaskEntry) -> None:
        """
        Place task at the back of its priority bucket for retry scheduling.
        Used after failure to respect exponential backoff ordering.
        """
        task.status = "awaiting_retry"
        if task.priority not in self._buckets:
            self._buckets[task.priority] = deque()
        task.sequence_num = self._sequence_counter
        self._sequence_counter += 1
        self._buckets[task.priority].append(task)
        self._size += 1

    def get_queue_state(self) -> dict:
        """Return current state of all priority buckets."""
        state = {}
        for priority in sorted(self._buckets.keys()):
            bucket = self._buckets[priority]
            if bucket:
                state[priority] = [t.task_id for t in bucket]
        return state

    def get_pending_count_by_priority(self) -> dict:
        """Return count of pending tasks per priority level."""
        counts = {}
        for priority, bucket in self._buckets.items():
            if bucket:
                counts[priority] = len(bucket)
        return counts

    def drain(self) -> list:
        """Remove and return all remaining tasks."""
        remaining = []
        for priority in sorted(self._buckets.keys()):
            while self._buckets[priority]:
                remaining.append(self._buckets[priority].popleft())
                self._size -= 1
        return remaining

    def contains(self, task_id: str) -> bool:
        """Check if a task is currently in the queue."""
        for bucket in self._buckets.values():
            for task in bucket:
                if task.task_id == task_id:
                    return True
        return False
