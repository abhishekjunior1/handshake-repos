"""
DAG loader for the work-stealing scheduler simulator.

Loads task dependency graphs from JSON configuration files. Validates
the graph structure (acyclic, valid references) and builds TaskDescriptor
objects for the scheduler.

Input format:
{
  "config": {
    "num_workers": int,
    "numa_nodes": int,
    "adjacent_steal_only": bool,
    "idle_spin_enabled": bool,
    "max_ticks": int
  },
  "tasks": [
    {
      "id": str,
      "execution_cost": int,
      "dependencies": [str, ...],
      "priority": float (optional),
      "worker_affinity": int (optional)
    },
    ...
  ]
}
"""

import json
from typing import Tuple
from task_queue import TaskDescriptor


class DAGValidationError(Exception):
    """Raised when the task DAG is invalid."""
    pass


def load_schedule(input_path: str) -> Tuple[dict, list[TaskDescriptor]]:
    """Load a schedule configuration and task list from JSON.

    Args:
        input_path: Path to the JSON schedule file

    Returns:
        Tuple of (config dict, list of TaskDescriptor)

    Raises:
        DAGValidationError: If the DAG is invalid (cycles, missing deps)
    """
    with open(input_path, 'r') as f:
        data = json.load(f)

    config = data["config"]
    raw_tasks = data["tasks"]

    # Validate task IDs are unique
    task_ids = set()
    for t in raw_tasks:
        if t["id"] in task_ids:
            raise DAGValidationError(f"Duplicate task ID: {t['id']}")
        task_ids.add(t["id"])

    # Validate dependency references
    for t in raw_tasks:
        for dep in t.get("dependencies", []):
            if dep not in task_ids:
                raise DAGValidationError(
                    f"Task {t['id']} depends on unknown task {dep}")

    # Build TaskDescriptor objects
    tasks = []
    for i, t in enumerate(raw_tasks):
        task = TaskDescriptor(
            task_id=t["id"],
            priority=t.get("priority", 1.0),
            critical_path_length=0.0,  # Computed later by scheduler
            submission_order=i,
            dependencies=t.get("dependencies", []),
            execution_cost=t["execution_cost"],
            worker_affinity=t.get("worker_affinity", None)
        )
        tasks.append(task)

    # Validate no cycles
    _check_acyclic(tasks)

    return config, tasks


def _check_acyclic(tasks: list[TaskDescriptor]) -> None:
    """Verify the dependency graph is a DAG (no cycles).

    Uses DFS-based cycle detection with coloring:
    WHITE=unvisited, GRAY=in-progress, BLACK=completed
    """
    task_map = {t.task_id: t for t in tasks}
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {t.task_id: WHITE for t in tasks}

    def dfs(task_id: str) -> None:
        color[task_id] = GRAY
        task = task_map[task_id]
        for dep_id in task.dependencies:
            if color[dep_id] == GRAY:
                raise DAGValidationError(
                    f"Cycle detected involving task {dep_id}")
            if color[dep_id] == WHITE:
                dfs(dep_id)
        color[task_id] = BLACK

    for task_id in task_map:
        if color[task_id] == WHITE:
            dfs(task_id)


def get_root_tasks(tasks: list[TaskDescriptor]) -> list[TaskDescriptor]:
    """Find tasks with no dependencies (entry points of the DAG)."""
    return [t for t in tasks if not t.dependencies]


def get_leaf_tasks(tasks: list[TaskDescriptor]) -> list[TaskDescriptor]:
    """Find tasks that no other task depends on (exit points)."""
    all_ids = {t.task_id for t in tasks}
    depended_on = set()
    for t in tasks:
        for dep in t.dependencies:
            depended_on.add(dep)
    leaf_ids = all_ids - depended_on
    return [t for t in tasks if t.task_id in leaf_ids]


def compute_total_work(tasks: list[TaskDescriptor]) -> int:
    """Compute total execution cost across all tasks."""
    return sum(t.execution_cost for t in tasks)
