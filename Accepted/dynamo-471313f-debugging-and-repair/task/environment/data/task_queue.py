"""
Work-stealing deque implementation for the scheduler simulator.

Each worker maintains a double-ended queue (deque). The owner pushes and pops
from the BOTTOM (LIFO for local work). Thieves steal from the TOP (oldest tasks
first — this ensures breadth-first distribution of stolen work).

The deque supports three operations:
  - push_bottom: Owner adds a new task (spawned subtask)
  - pop_bottom: Owner takes its next task (LIFO — depth-first execution)
  - steal_top: Thief takes from the opposite end (FIFO steal — breadth-first)
"""

from typing import Any, Optional


class WorkStealingDeque:
    """A double-ended queue supporting push/pop at bottom and steal at top."""

    def __init__(self, worker_id: int):
        self.worker_id = worker_id
        self._items: list = []

    def push_bottom(self, task: Any) -> None:
        """Owner pushes a task to the bottom of the deque."""
        self._items.append(task)

    def pop_bottom(self) -> Optional[Any]:
        """Owner pops from the bottom (LIFO). Returns None if empty."""
        if not self._items:
            return None
        return self._items.pop()

    def steal_top(self) -> Optional[Any]:
        """Thief steals from the top of the deque (oldest task first).

        Work-stealing convention: thieves take from the TOP (index 0) to
        distribute breadth-first work across workers, while the owner
        processes depth-first from the BOTTOM.
        """
        if not self._items:
            return None
        return self._items.pop(0)

    def size(self) -> int:
        """Return the current number of tasks in the deque."""
        return len(self._items)

    def is_empty(self) -> bool:
        """Check if the deque has no tasks."""
        return len(self._items) == 0

    def peek_top(self) -> Optional[Any]:
        """Peek at the top element without removing it."""
        if not self._items:
            return None
        return self._items[0]

    def peek_bottom(self) -> Optional[Any]:
        """Peek at the bottom element without removing it."""
        if not self._items:
            return None
        return self._items[-1]


class TaskDescriptor:
    """Describes a schedulable task unit in the DAG."""

    def __init__(self, task_id: str, priority: float, critical_path_length: float,
                 submission_order: int, dependencies: list, execution_cost: int,
                 worker_affinity: Optional[int] = None):
        self.task_id = task_id
        self.priority = priority
        self.critical_path_length = critical_path_length
        self.submission_order = submission_order
        self.dependencies = list(dependencies)
        self.execution_cost = execution_cost
        self.worker_affinity = worker_affinity
        self.start_time: Optional[int] = None
        self.finish_time: Optional[int] = None
        self.assigned_worker: Optional[int] = None
        self.stolen = False

    def is_ready(self, completed_tasks: dict) -> bool:
        """Check if all dependencies are satisfied."""
        for dep_id in self.dependencies:
            if dep_id not in completed_tasks:
                return False
        return True

    def get_earliest_start(self, completed_tasks: dict) -> int:
        """Compute earliest possible start based on dependency finish times."""
        if not self.dependencies:
            return 0
        max_dep_finish = 0
        for dep_id in self.dependencies:
            if dep_id in completed_tasks:
                dep_finish = completed_tasks[dep_id]
                if dep_finish > max_dep_finish:
                    max_dep_finish = dep_finish
        return max_dep_finish

    def __repr__(self) -> str:
        return f"Task({self.task_id}, cost={self.execution_cost}, deps={self.dependencies})"


class PriorityTaskQueue:
    """A priority queue for tasks awaiting scheduling.

    Tasks are ordered by their scheduling priority. The scheduler uses
    critical_path_length as the primary sort key — tasks on the longest
    path through the DAG are scheduled first to minimize makespan.
    """

    def __init__(self):
        self._queue: list = []

    def enqueue(self, task: TaskDescriptor, sort_key: float) -> None:
        """Insert a task with the given sort key (lower = higher priority)."""
        entry = (sort_key, task.submission_order, task)
        self._queue.append(entry)
        self._queue.sort(key=lambda x: (x[0], x[1]))

    def dequeue(self) -> Optional[TaskDescriptor]:
        """Remove and return the highest-priority task."""
        if not self._queue:
            return None
        return self._queue.pop(0)[2]

    def peek(self) -> Optional[TaskDescriptor]:
        """Look at the highest-priority task without removing it."""
        if not self._queue:
            return None
        return self._queue[0][2]

    def size(self) -> int:
        """Return number of tasks in queue."""
        return len(self._queue)

    def is_empty(self) -> bool:
        """Check if queue is empty."""
        return len(self._queue) == 0

    def remove_task(self, task_id: str) -> Optional[TaskDescriptor]:
        """Remove a specific task by ID."""
        for i, (_, _, task) in enumerate(self._queue):
            if task.task_id == task_id:
                return self._queue.pop(i)[2]
        return None
