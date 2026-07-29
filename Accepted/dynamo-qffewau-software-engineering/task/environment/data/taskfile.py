"""Taskfile parser for JSON-based task definitions.

Parses task definitions from a JSON taskfile including commands,
dependencies, environment variables, conditions, and execution settings.
"""

import os
import logging
from config import load_json, validate_file_exists

logger = logging.getLogger("taskrunner.taskfile")


class TaskDefinition:
    """Represents a single task with its configuration."""

    def __init__(self, name, commands, dependencies=None, env=None,
                 conditions=None, workdir=None, description="",
                 priority=0, retries=0, parallel_group=None):
        self.name = name
        self.commands = commands
        self.dependencies = dependencies or []
        self.env = env or {}
        self.conditions = conditions or {}
        self.workdir = workdir
        self.description = description
        self.priority = priority
        self.retries = retries
        self.parallel_group = parallel_group

    def has_preconditions(self):
        """Check if task has preconditions defined."""
        return "pre" in self.conditions and len(self.conditions["pre"]) > 0

    def has_postconditions(self):
        """Check if task has postconditions defined."""
        return "post" in self.conditions and len(self.conditions["post"]) > 0

    def get_preconditions(self):
        """Get the list of preconditions."""
        return self.conditions.get("pre", [])

    def get_postconditions(self):
        """Get the list of postconditions."""
        return self.conditions.get("post", [])

    def get_effective_retries(self):
        """Get the effective retry count (minimum 0)."""
        return max(0, self.retries)

    def __repr__(self):
        return (f"TaskDefinition(name={self.name!r}, priority={self.priority}, "
                f"deps={self.dependencies})")


class TaskfileParser:
    """Parses and validates JSON taskfile definitions."""

    def __init__(self, filepath):
        self.filepath = filepath
        self.tasks = {}
        self.metadata = {}
        self.settings = {}

    def parse(self):
        """Parse the taskfile and return task definitions."""
        validate_file_exists(self.filepath)
        data = load_json(self.filepath)
        self.metadata = data.get("metadata", {})
        self.settings = data.get("settings", {})
        raw_tasks = data.get("tasks", {})
        for name, task_data in raw_tasks.items():
            self._parse_task(name, task_data)
        logger.info(f"Parsed {len(self.tasks)} tasks from {self.filepath}")
        return self.tasks

    def _parse_task(self, name, data):
        """Parse a single task definition from raw data."""
        commands = data.get("commands", [])
        if isinstance(commands, str):
            commands = [commands]
        dependencies = data.get("dependencies", [])
        env = data.get("env", {})
        conditions = data.get("conditions", {})
        workdir = data.get("workdir", None)
        description = data.get("description", "")
        priority = data.get("priority", 0)
        retries = data.get("retries", 0)
        parallel_group = data.get("parallel_group", None)
        task = TaskDefinition(
            name=name,
            commands=commands,
            dependencies=dependencies,
            env=env,
            conditions=conditions,
            workdir=workdir,
            description=description,
            priority=priority,
            retries=retries,
            parallel_group=parallel_group,
        )
        self.tasks[name] = task
        return task

    def get_task(self, name):
        """Get a specific task definition by name."""
        if name not in self.tasks:
            raise KeyError(f"Task '{name}' not found in taskfile")
        return self.tasks[name]

    def get_all_task_names(self):
        """Get all task names in declaration order."""
        return list(self.tasks.keys())

    def get_parallelism(self):
        """Get the configured parallelism level."""
        return self.settings.get("parallelism", 1)

    def get_retry_policy(self):
        """Get the configured retry policy."""
        return self.settings.get("retry_policy", "preserve_state")

    def validate_dependencies(self):
        """Validate that all dependency references are valid."""
        all_names = set(self.tasks.keys())
        for name, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in all_names:
                    raise ValueError(
                        f"Task '{name}' depends on unknown task '{dep}'"
                    )
        return True

    def get_metadata(self):
        """Get taskfile metadata."""
        return self.metadata

    def get_entry_points(self):
        """Find tasks that are not depended on by any other task."""
        all_deps = set()
        for task in self.tasks.values():
            all_deps.update(task.dependencies)
        return [n for n in self.tasks if n not in all_deps]

    def get_leaf_tasks(self):
        """Find tasks with no dependencies."""
        return [
            n for n, t in self.tasks.items()
            if not t.dependencies
        ]

    def get_task_graph(self):
        """Get a simplified graph representation of all tasks."""
        graph = {}
        for name, task in self.tasks.items():
            graph[name] = {
                "dependencies": task.dependencies,
                "priority": task.priority,
                "retries": task.retries,
            }
        return graph
