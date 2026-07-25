"""
Synchronization primitives for the deterministic scheduler simulator.

Provides simulated synchronization mechanisms used by the work-stealing
runtime. These are NOT actual OS primitives — they simulate the LOGIC
of synchronization in a deterministic tick-based model.

Includes:
  - Steal protocol (CAS-like atomic steal simulation)
  - Idle spin backoff (exponential backoff before stealing)
  - Dependency barriers (track when all predecessors complete)
"""

from typing import Optional
from task_queue import TaskDescriptor


class StealProtocol:
    """Simulates the atomic compare-and-swap protocol for work stealing.

    In real work-stealing runtimes, the steal operation uses CAS to atomically
    remove a task from the victim's deque. This simulation models the success/
    failure of steal attempts based on deque state.
    """

    def __init__(self):
        self.total_attempts = 0
        self.total_successes = 0
        self.total_failures = 0
        self.contention_events = 0

    def attempt_steal(self, victim_deque_size: int, concurrent_thieves: int) -> bool:
        """Simulate whether a steal attempt succeeds.

        In a real CAS-based implementation, contention from multiple thieves
        causes some attempts to fail. We model this deterministically:
        steal succeeds if the victim has tasks AND no prior thief took
        from the same position in this tick.

        Args:
            victim_deque_size: Number of tasks in the victim's deque
            concurrent_thieves: Number of other workers also trying to steal this tick

        Returns:
            True if the steal would succeed
        """
        self.total_attempts += 1
        if victim_deque_size == 0:
            self.total_failures += 1
            return False
        # Deterministic contention model: first thief always wins
        # (simulation processes thieves in worker_id order)
        if concurrent_thieves > 0:
            self.contention_events += 1
        self.total_successes += 1
        return True

    def get_statistics(self) -> dict:
        """Return steal protocol statistics."""
        success_rate = 0.0
        if self.total_attempts > 0:
            success_rate = self.total_successes / self.total_attempts
        return {
            "total_attempts": self.total_attempts,
            "total_successes": self.total_successes,
            "total_failures": self.total_failures,
            "success_rate": round(success_rate, 6),
            "contention_events": self.contention_events
        }


class IdleSpinBackoff:
    """Implements exponential backoff for idle workers before stealing.

    Workers spin for an increasing number of ticks before attempting to steal.
    This reduces contention on victim deques when multiple workers go idle
    simultaneously. The backoff sequence is:
      1, 2, 4, 8, ... up to max_spin_ticks

    This is a standard optimization in work-stealing runtimes (Cilk, Tokio)
    to avoid thundering-herd steal attempts.
    """

    def __init__(self, initial_spin: int = 1, max_spin: int = 8,
                 backoff_factor: int = 2):
        self.initial_spin = initial_spin
        self.max_spin = max_spin
        self.backoff_factor = backoff_factor

    def get_spin_duration(self, consecutive_idle_ticks: int) -> int:
        """Compute how many ticks to spin before next steal attempt.

        The spin duration doubles with each failed steal, up to max_spin.
        This gives recently-idle workers fast steal response while preventing
        long-idle workers from constantly contending.

        Args:
            consecutive_idle_ticks: How many ticks this worker has been idle

        Returns:
            Number of ticks to spin before next steal attempt
        """
        # Compute backoff level from consecutive idle time
        if consecutive_idle_ticks == 0:
            return self.initial_spin
        level = 0
        threshold = self.initial_spin
        accumulated = 0
        while accumulated + threshold <= consecutive_idle_ticks:
            accumulated += threshold
            level += 1
            threshold = min(self.initial_spin * (self.backoff_factor ** level),
                           self.max_spin)
        return min(self.initial_spin * (self.backoff_factor ** level), self.max_spin)

    def should_attempt_steal(self, idle_ticks: int, last_steal_tick: int,
                             current_tick: int) -> bool:
        """Determine if a worker should attempt stealing at this tick.

        Workers wait for the computed spin duration between steal attempts.
        This reduces contention on victim deques.

        Args:
            idle_ticks: Consecutive idle ticks for this worker
            last_steal_tick: Tick when last steal attempt was made
            current_tick: Current simulation tick

        Returns:
            True if the worker should try to steal now
        """
        if last_steal_tick == 0:
            return True  # First attempt always goes immediately
        spin_duration = self.get_spin_duration(idle_ticks)
        return (current_tick - last_steal_tick) >= spin_duration


class DependencyBarrier:
    """Tracks dependency completion for tasks with multiple predecessors.

    Each task has a counter of unsatisfied dependencies. When the counter
    reaches zero, the task becomes ready for scheduling.
    """

    def __init__(self):
        self._pending_counts: dict[str, int] = {}
        self._dependency_finish_times: dict[str, dict[str, int]] = {}

    def register_task(self, task: TaskDescriptor) -> None:
        """Register a task's dependency count."""
        self._pending_counts[task.task_id] = len(task.dependencies)
        self._dependency_finish_times[task.task_id] = {}

    def signal_completion(self, completed_task_id: str, finish_time: int,
                          dependent_tasks: list[str]) -> list[str]:
        """Signal that a task completed, potentially releasing dependents.

        Args:
            completed_task_id: The task that just finished
            finish_time: When it finished
            dependent_tasks: Tasks that depend on the completed task

        Returns:
            List of task IDs that became ready (all deps satisfied)
        """
        newly_ready = []
        for dep_id in dependent_tasks:
            if dep_id not in self._pending_counts:
                continue
            # Record the finish time of this dependency
            self._dependency_finish_times.setdefault(dep_id, {})
            self._dependency_finish_times[dep_id][completed_task_id] = finish_time
            self._pending_counts[dep_id] -= 1
            if self._pending_counts[dep_id] <= 0:
                newly_ready.append(dep_id)
        return newly_ready

    def get_max_dependency_finish_time(self, task_id: str) -> int:
        """Get the latest finish time among a task's dependencies.

        This determines the earliest possible start time for the task.
        """
        dep_times = self._dependency_finish_times.get(task_id, {})
        if not dep_times:
            return 0
        return max(dep_times.values())

    def is_ready(self, task_id: str) -> bool:
        """Check if a task has all dependencies satisfied."""
        return self._pending_counts.get(task_id, 0) <= 0

    def get_pending_count(self, task_id: str) -> int:
        """Get remaining unsatisfied dependency count."""
        return self._pending_counts.get(task_id, 0)
