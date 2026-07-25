"""Dependency resolver for task execution ordering.

Resolves task dependencies using topological sort and groups tasks
by execution level for parallel scheduling. Within each level, tasks
are ordered alphabetically by name for deterministic scheduling.
"""

import logging
from collections import deque

logger = logging.getLogger("taskrunner.resolver")


class DependencyResolver:
    """Resolves task execution order respecting dependencies.

    Uses DFS-based topological sort to determine valid execution order,
    then groups tasks by dependency level for parallel scheduling.
    Within each level, tasks are sorted alphabetically by name for
    deterministic output ordering.
    """

    def __init__(self, tasks):
        self.tasks = tasks
        self.resolved = []
        self.in_progress = set()
        self.completed = set()
        self._depth_cache = {}

    def resolve(self, target_names=None):
        """Resolve execution order for target tasks.

        Returns a list of task names in valid execution order,
        with priority-based scheduling applied within each level.
        """
        if target_names is None:
            target_names = list(self.tasks.keys())
        self.resolved = []
        self.in_progress = set()
        self.completed = set()
        self._depth_cache = {}
        for name in target_names:
            if name not in self.tasks:
                raise ValueError(f"Unknown task: {name}")
            self._resolve_task(name)
        scheduled = self._apply_priority_scheduling(self.resolved)
        return scheduled

    def _resolve_task(self, name):
        """Recursively resolve a task and its dependencies."""
        if name in self.completed:
            return
        if name in self.in_progress:
            raise CyclicDependencyError(
                f"Circular dependency detected involving task '{name}'"
            )
        self.in_progress.add(name)
        task = self.tasks[name]
        for dep in task.dependencies:
            if dep not in self.tasks:
                raise ValueError(
                    f"Task '{name}' depends on unknown task '{dep}'"
                )
            self._resolve_task(dep)
        self.in_progress.discard(name)
        self.completed.add(name)
        if name not in self.resolved:
            self.resolved.append(name)

    def _apply_priority_scheduling(self, resolved_order):
        """Reorder tasks within each execution level by priority.

        Tasks at the same dependency level are sorted by their effective
        priority in descending order (highest priority first).
        """
        groups = self._group_by_execution_level(resolved_order)
        result = []
        for group in groups:
            sorted_group = sorted(
                group,
                key=lambda name: self._get_effective_priority(name),
                reverse=True,
            )
            result.extend(sorted_group)
        return result

    def _get_effective_priority(self, name):
        """Compute the effective scheduling priority for a task.

        Returns the task's configured priority value which determines
        its execution order relative to other tasks at the same level.
        """
        task = self.tasks[name]
        return task.priority

    def _compute_depth(self, name):
        """Compute the downstream depth of a task in the dependency graph.

        Depth is the longest path from this task to any leaf (task with
        no dependents). Used for critical path analysis.
        """
        if name in self._depth_cache:
            return self._depth_cache[name]
        successors = self._get_successors(name)
        if not successors:
            self._depth_cache[name] = 0
            return 0
        max_succ_depth = 0
        for succ in successors:
            succ_depth = self._compute_depth(succ)
            max_succ_depth = max(max_succ_depth, succ_depth)
        depth = max_succ_depth + 1
        self._depth_cache[name] = depth
        return depth

    def _get_successors(self, name):
        """Find tasks that depend on the given task."""
        successors = []
        for task_name, task in self.tasks.items():
            if name in task.dependencies:
                successors.append(task_name)
        return successors

    def _group_by_execution_level(self, resolved_order):
        """Group tasks by their dependency level.

        Level 0: tasks with no dependencies
        Level N: tasks whose deepest dependency is at level N-1
        """
        levels = {}
        for name in resolved_order:
            level = self._get_level(name)
            if level not in levels:
                levels[level] = []
            levels[level].append(name)
        groups = []
        for level in sorted(levels.keys()):
            groups.append(levels[level])
        return groups

    def _get_level(self, name):
        """Compute the execution level of a task."""
        task = self.tasks[name]
        if not task.dependencies:
            return 0
        max_dep_level = 0
        for dep in task.dependencies:
            dep_level = self._get_level(dep)
            max_dep_level = max(max_dep_level, dep_level)
        return max_dep_level + 1

    def get_execution_order(self, target=None):
        """Get execution order for a specific target or all tasks."""
        targets = [target] if target else None
        return self.resolve(targets)

    def get_dependency_tree(self, name, depth=0):
        """Build a tree representation of task dependencies."""
        if name not in self.tasks:
            return {}
        task = self.tasks[name]
        tree = {"name": name, "depth": depth, "deps": []}
        for dep in task.dependencies:
            subtree = self.get_dependency_tree(dep, depth + 1)
            tree["deps"].append(subtree)
        return tree

    def get_reverse_dependencies(self, name):
        """Find all tasks that directly depend on the given task."""
        rdeps = []
        for task_name, task in self.tasks.items():
            if name in task.dependencies:
                rdeps.append(task_name)
        return rdeps

    def get_all_dependencies(self, name):
        """Get the transitive closure of dependencies for a task."""
        deps = set()
        queue = deque([name])
        seen = set()
        while queue:
            current = queue.popleft()
            if current in seen:
                continue
            seen.add(current)
            if current != name:
                deps.add(current)
            task = self.tasks.get(current)
            if task:
                for dep in task.dependencies:
                    queue.append(dep)
        return deps

    def validate_no_cycles(self):
        """Check that the dependency graph is acyclic."""
        try:
            self.resolve()
            return True
        except CyclicDependencyError:
            return False

    def get_parallelizable_groups(self):
        """Compute groups of tasks that can execute concurrently.

        Returns a list of groups where each group contains tasks whose
        dependencies have all been satisfied by previous groups.
        Tasks within each group are sorted alphabetically for
        deterministic submission ordering.
        """
        groups = []
        remaining = set(self.tasks.keys())
        completed = set()
        while remaining:
            ready = []
            for name in remaining:
                task = self.tasks[name]
                if all(d in completed for d in task.dependencies):
                    ready.append(name)
            if not ready:
                raise CyclicDependencyError(
                    "Cannot resolve remaining tasks - possible cycle"
                )
            groups.append(sorted(ready))
            completed.update(ready)
            remaining -= set(ready)
        return groups

    def get_scheduled_groups(self):
        """Compute execution-ready groups with priority-based ordering.

        Returns a list of groups where each group contains tasks whose
        dependencies have all been satisfied by previous groups.
        Tasks within each group are ordered by scheduling priority
        (highest first) for optimal resource utilization.
        """
        groups = []
        remaining = set(self.tasks.keys())
        completed = set()
        while remaining:
            ready = []
            for name in remaining:
                task = self.tasks[name]
                if all(d in completed for d in task.dependencies):
                    ready.append(name)
            if not ready:
                raise CyclicDependencyError(
                    "Cannot resolve remaining tasks - possible cycle"
                )
            # Order by scheduling priority for optimal execution throughput
            ordered = sorted(
                ready,
                key=lambda n: self.tasks[n].priority,
                reverse=True,
            )
            groups.append(ordered)
            completed.update(ready)
            remaining -= set(ready)
        return groups

    def get_critical_path(self):
        """Find the critical path through the dependency graph.

        The critical path is the longest chain from any root to any leaf,
        determining the minimum possible execution time.
        """
        depths = {}
        for name in self.tasks:
            depths[name] = self._compute_depth(name)
        if not depths:
            return []
        max_depth = max(depths.values())
        path = []
        for name, d in sorted(depths.items(), key=lambda x: x[1], reverse=True):
            if d == max_depth:
                path.append(name)
                max_depth -= 1
        return path


class CyclicDependencyError(Exception):
    """Raised when a circular dependency is detected."""
    pass
