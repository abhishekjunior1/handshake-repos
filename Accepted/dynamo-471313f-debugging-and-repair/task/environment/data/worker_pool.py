"""
Worker pool management for the work-stealing scheduler simulator.

Manages a pool of simulated worker threads, each with:
  - A local work-stealing deque
  - Execution state (idle, executing, stealing)
  - NUMA topology information for steal-distance calculation
  - Idle spin counters for backoff before stealing

Workers are organized in a linear NUMA topology where adjacent workers
share cache resources. The steal policy restricts stealing to adjacent
workers to preserve cache locality — this is a standard optimization
in production work-stealing runtimes (e.g., Cilk, TBB).
"""

from typing import Optional
from task_queue import WorkStealingDeque, TaskDescriptor


class WorkerState:
    """Tracks the execution state of a single simulated worker."""

    IDLE = "idle"
    EXECUTING = "executing"
    STEALING = "stealing"
    SPINNING = "spinning"

    def __init__(self, worker_id: int, numa_node: int):
        self.worker_id = worker_id
        self.numa_node = numa_node
        self.state = self.IDLE
        self.deque = WorkStealingDeque(worker_id)
        self.current_task: Optional[TaskDescriptor] = None
        self.task_start_tick: Optional[int] = None
        self.idle_spin_counter = 0
        self.total_tasks_executed = 0
        self.total_tasks_stolen = 0
        self.total_idle_ticks = 0
        self.total_execution_ticks = 0
        self.steal_attempts = 0
        self.steal_successes = 0

    def begin_execution(self, task: TaskDescriptor, tick: int) -> None:
        """Start executing a task at the given simulation tick."""
        self.state = self.EXECUTING
        self.current_task = task
        self.task_start_tick = tick
        task.start_time = tick
        task.assigned_worker = self.worker_id
        self.idle_spin_counter = 0

    def complete_execution(self, tick: int) -> TaskDescriptor:
        """Mark current task as complete. Returns the completed task."""
        task = self.current_task
        task.finish_time = tick
        self.current_task = None
        self.task_start_tick = None
        self.state = self.IDLE
        self.total_tasks_executed += 1
        self.total_execution_ticks += (tick - task.start_time)
        return task

    def is_idle(self) -> bool:
        """Check if worker has no current task."""
        return self.state == self.IDLE or self.state == self.SPINNING

    def is_executing(self) -> bool:
        """Check if worker is currently executing a task."""
        return self.state == self.EXECUTING

    def increment_idle(self) -> None:
        """Track idle time."""
        self.total_idle_ticks += 1
        self.idle_spin_counter += 1

    def record_steal_attempt(self, success: bool) -> None:
        """Record a steal attempt."""
        self.steal_attempts += 1
        if success:
            self.steal_successes += 1
            self.total_tasks_stolen += 1

    def get_utilization(self, total_ticks: int) -> float:
        """Compute worker utilization as fraction of time executing."""
        if total_ticks == 0:
            return 0.0
        return self.total_execution_ticks / total_ticks


class WorkerPool:
    """Manages a pool of worker threads with NUMA topology."""

    def __init__(self, num_workers: int, numa_nodes: int = 1):
        self.num_workers = num_workers
        self.numa_nodes = numa_nodes
        self.workers: list[WorkerState] = []
        self._init_workers()

    def _init_workers(self) -> None:
        """Initialize workers distributed across NUMA nodes."""
        workers_per_node = max(1, self.num_workers // self.numa_nodes)
        for wid in range(self.num_workers):
            numa_node = wid // workers_per_node
            if numa_node >= self.numa_nodes:
                numa_node = self.numa_nodes - 1
            self.workers.append(WorkerState(wid, numa_node))

    def get_worker(self, worker_id: int) -> WorkerState:
        """Get a worker by ID."""
        return self.workers[worker_id]

    def get_idle_workers(self) -> list[WorkerState]:
        """Return all idle workers."""
        return [w for w in self.workers if w.is_idle()]

    def get_busy_workers(self) -> list[WorkerState]:
        """Return all busy workers."""
        return [w for w in self.workers if w.is_executing()]

    def get_adjacent_workers(self, worker_id: int) -> list[int]:
        """Get workers adjacent in NUMA topology (same or neighboring node).

        Adjacent workers share cache hierarchy, making stolen data more likely
        to be warm in shared caches. This is the standard NUMA-aware steal
        restriction used in Intel TBB and similar runtimes.
        """
        worker = self.workers[worker_id]
        adjacent = []
        for other in self.workers:
            if other.worker_id == worker_id:
                continue
            # Adjacent = same NUMA node or immediately neighboring node
            if abs(other.numa_node - worker.numa_node) <= 1:
                adjacent.append(other.worker_id)
        return adjacent

    def get_all_potential_victims(self, worker_id: int) -> list[int]:
        """Get all workers that could be steal victims (excluding self)."""
        return [w.worker_id for w in self.workers if w.worker_id != worker_id]

    def get_steal_candidates(self, worker_id: int, adjacent_only: bool) -> list[int]:
        """Get valid steal candidates based on topology constraint.

        Args:
            worker_id: The stealing worker
            adjacent_only: If True, restrict to NUMA-adjacent workers only
        """
        if adjacent_only:
            return self.get_adjacent_workers(worker_id)
        return self.get_all_potential_victims(worker_id)

    def get_richest_victim(self, candidates: list[int]) -> Optional[int]:
        """Find the candidate with the most tasks in their deque.

        Standard heuristic: steal from the busiest worker to balance load.
        """
        best_victim = None
        best_size = 0
        for wid in candidates:
            worker = self.workers[wid]
            if worker.deque.size() > best_size:
                best_size = worker.deque.size()
                best_victim = wid
        return best_victim

    def get_pool_statistics(self, total_ticks: int) -> dict:
        """Compute aggregate statistics for the worker pool."""
        stats = {
            "num_workers": self.num_workers,
            "total_tasks_executed": sum(w.total_tasks_executed for w in self.workers),
            "total_steals": sum(w.total_tasks_stolen for w in self.workers),
            "total_steal_attempts": sum(w.steal_attempts for w in self.workers),
            "per_worker": []
        }
        for w in self.workers:
            stats["per_worker"].append({
                "worker_id": w.worker_id,
                "tasks_executed": w.total_tasks_executed,
                "tasks_stolen": w.total_tasks_stolen,
                "utilization": round(w.get_utilization(total_ticks), 6),
                "idle_ticks": w.total_idle_ticks,
                "execution_ticks": w.total_execution_ticks
            })
        return stats
