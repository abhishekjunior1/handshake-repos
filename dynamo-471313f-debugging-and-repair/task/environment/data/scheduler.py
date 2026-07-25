"""
Scheduler module for the work-stealing runtime simulator.

Implements the core scheduling decisions:
  - Task readiness evaluation (dependency resolution)
  - Priority computation (critical path length)
  - Work distribution to idle workers
  - Makespan tracking

The scheduler uses critical-path-length (CPL) as the primary scheduling key.
Tasks on the longest path through the dependency DAG are scheduled first,
which is the standard heuristic for minimizing parallel makespan (proven
optimal for tree-structured DAGs).
"""

from typing import Optional
from task_queue import TaskDescriptor, PriorityTaskQueue


class DependencyGraph:
    """Manages task dependency relationships and critical path computation."""

    def __init__(self):
        self.tasks: dict[str, TaskDescriptor] = {}
        self.successors: dict[str, list[str]] = {}
        self.predecessors: dict[str, list[str]] = {}
        self._critical_paths: dict[str, float] = {}

    def add_task(self, task: TaskDescriptor) -> None:
        """Register a task in the dependency graph."""
        self.tasks[task.task_id] = task
        self.successors.setdefault(task.task_id, [])
        self.predecessors[task.task_id] = list(task.dependencies)
        for dep_id in task.dependencies:
            self.successors.setdefault(dep_id, [])
            self.successors[dep_id].append(task.task_id)

    def compute_critical_paths(self) -> dict[str, float]:
        """Compute critical path length for each task using bottom-up traversal.

        CPL(task) = execution_cost(task) + max(CPL(successor) for all successors)
        Leaf tasks have CPL = their own execution cost.
        """
        self._critical_paths = {}
        # Process in reverse topological order (leaves first)
        visited = set()
        order = []
        self._topo_sort_reverse(visited, order)

        for task_id in order:
            task = self.tasks[task_id]
            successor_max = 0.0
            for succ_id in self.successors.get(task_id, []):
                if succ_id in self._critical_paths:
                    succ_cpl = self._critical_paths[succ_id]
                    if succ_cpl > successor_max:
                        successor_max = succ_cpl
            self._critical_paths[task_id] = task.execution_cost + successor_max

        return dict(self._critical_paths)

    def _topo_sort_reverse(self, visited: set, order: list) -> None:
        """Reverse topological sort — leaves come first."""
        in_progress = set()
        for task_id in self.tasks:
            if task_id not in visited:
                self._dfs_reverse(task_id, visited, in_progress, order)

    def _dfs_reverse(self, task_id: str, visited: set, in_progress: set,
                     order: list) -> None:
        """DFS for reverse topological ordering."""
        if task_id in visited:
            return
        in_progress.add(task_id)
        for succ_id in self.successors.get(task_id, []):
            if succ_id in self.tasks and succ_id not in visited:
                self._dfs_reverse(succ_id, visited, in_progress, order)
        visited.add(task_id)
        in_progress.discard(task_id)
        order.append(task_id)

    def get_critical_path_length(self, task_id: str) -> float:
        """Get precomputed critical path length for a task."""
        return self._critical_paths.get(task_id, 0.0)

    def get_ready_tasks(self, completed_tasks: dict) -> list[TaskDescriptor]:
        """Find all tasks whose dependencies are fully satisfied."""
        ready = []
        for task_id, task in self.tasks.items():
            if task.start_time is not None:
                continue  # Already started
            if task.is_ready(completed_tasks):
                ready.append(task)
        return ready


class SchedulerEngine:
    """Core scheduling engine that assigns ready tasks to workers.

    Scheduling priority is determined by critical_path_length — tasks on the
    longest remaining path are scheduled first to minimize overall makespan.
    This is the standard List Scheduling heuristic (Graham 1966).
    """

    def __init__(self, config: dict):
        self.config = config
        self.ready_queue = PriorityTaskQueue()
        self.dependency_graph = DependencyGraph()
        self.completed_tasks: dict[str, int] = {}  # task_id -> finish_time
        self.task_order: list[str] = []  # Completion order
        self.current_tick = 0

    def initialize_graph(self, tasks: list[TaskDescriptor]) -> None:
        """Build the dependency graph and compute critical paths."""
        for task in tasks:
            self.dependency_graph.add_task(task)
        self.dependency_graph.compute_critical_paths()

    def get_scheduling_priority(self, task: TaskDescriptor) -> float:
        """Compute scheduling priority for a task.

        Uses NEGATIVE critical path length so that longest-path tasks
        sort first (lower value = higher priority in the queue).
        """
        cpl = self.dependency_graph.get_critical_path_length(task.task_id)
        return -cpl  # Negative so longest path = highest priority

    def enqueue_ready_task(self, task: TaskDescriptor, sort_key: float) -> None:
        """Add a ready task to the scheduling queue with the given priority."""
        self.ready_queue.enqueue(task, sort_key)

    def dequeue_next_task(self) -> Optional[TaskDescriptor]:
        """Get the next task to schedule (highest priority = lowest sort key)."""
        return self.ready_queue.dequeue()

    def record_completion(self, task: TaskDescriptor, finish_time: int) -> None:
        """Record that a task completed at the given time."""
        self.completed_tasks[task.task_id] = finish_time
        self.task_order.append(task.task_id)

    def get_newly_ready_tasks(self) -> list[TaskDescriptor]:
        """Find tasks that became ready after latest completions."""
        ready = self.dependency_graph.get_ready_tasks(self.completed_tasks)
        return [t for t in ready if t.task_id not in
                {e[2].task_id for e in self.ready_queue._queue}]

    def get_makespan(self) -> int:
        """Return the total makespan (max finish time across all tasks)."""
        if not self.completed_tasks:
            return 0
        return max(self.completed_tasks.values())

    def get_schedule_summary(self) -> dict:
        """Return scheduling statistics."""
        return {
            "total_tasks": len(self.dependency_graph.tasks),
            "completed_tasks": len(self.completed_tasks),
            "makespan": self.get_makespan(),
            "completion_order": list(self.task_order),
            "critical_path_lengths": {
                tid: self.dependency_graph.get_critical_path_length(tid)
                for tid in self.dependency_graph.tasks
            }
        }
