"""Pre/post condition evaluator for task execution gates.

Evaluates conditions that must hold before a task starts (preconditions)
or after it completes (postconditions). Supports file existence checks,
command execution, environment variable verification, and file content checks.
"""

import os
import subprocess
import logging

from config import SHELL, resolve_path

logger = logging.getLogger("taskrunner.condition")


class ConditionEvaluator:
    """Evaluates task preconditions and postconditions.

    Conditions are evaluated against the current system state to determine
    whether a task should execute (preconditions) or has completed
    successfully (postconditions).
    """

    def __init__(self):
        self.results = {}

    def evaluate_preconditions(self, task):
        """Check all preconditions for a task. Returns True if all pass."""
        conditions = task.get_preconditions()
        if not conditions:
            return True
        for condition in conditions:
            if not self._evaluate_condition(condition, task):
                logger.info(
                    f"Precondition failed for task '{task.name}': {condition}"
                )
                return False
        return True

    def evaluate_postconditions(self, task):
        """Check all postconditions for a task. Returns True if all pass."""
        conditions = task.get_postconditions()
        if not conditions:
            return True
        for condition in conditions:
            if not self._evaluate_condition(condition, task):
                logger.warning(
                    f"Postcondition failed for task '{task.name}': {condition}"
                )
                return False
        return True

    def _evaluate_condition(self, condition, task):
        """Dispatch condition evaluation based on type."""
        cond_type = condition.get("type", "")
        if cond_type == "file_exists":
            return self._check_file_exists(condition, task)
        elif cond_type == "command":
            return self._check_command(condition, task)
        elif cond_type == "env_set":
            return self._check_env_set(condition, task)
        elif cond_type == "not_empty":
            return self._check_not_empty(condition, task)
        else:
            logger.warning(f"Unknown condition type: {cond_type}")
            return False

    def _check_file_exists(self, condition, task):
        """Check if a file exists at the specified path."""
        path = condition.get("path", "")
        if not os.path.isabs(path):
            base = task.workdir or os.getcwd()
            path = resolve_path(path, base)
        return os.path.exists(path)

    def _check_command(self, condition, task):
        """Execute a command and check its exit status."""
        command = condition.get("command", "")
        workdir = task.workdir or os.getcwd()
        try:
            proc = subprocess.run(
                command,
                shell=True,
                executable=SHELL,
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            return proc.returncode == 0
        except (subprocess.TimeoutExpired, OSError):
            return False

    def _check_env_set(self, condition, task):
        """Check if an environment variable is set and non-empty."""
        var_name = condition.get("variable", "")
        return var_name in os.environ and os.environ[var_name] != ""

    def _check_not_empty(self, condition, task):
        """Check if a file exists and has non-zero size."""
        path = condition.get("path", "")
        if not os.path.isabs(path):
            base = task.workdir or os.getcwd()
            path = resolve_path(path, base)
        if not os.path.isfile(path):
            return False
        return os.path.getsize(path) > 0

    def record_result(self, task_name, phase, passed):
        """Record a condition evaluation result."""
        key = f"{task_name}:{phase}"
        self.results[key] = passed

    def get_results(self):
        """Get all recorded condition results."""
        return dict(self.results)

    def reset(self):
        """Reset recorded results."""
        self.results = {}

    def evaluate_all_preconditions(self, tasks):
        """Evaluate preconditions for multiple tasks. Returns list of failures."""
        failed = []
        for task in tasks:
            if not self.evaluate_preconditions(task):
                failed.append(task.name)
        return failed

    def summarize(self):
        """Summarize condition evaluation statistics."""
        total = len(self.results)
        passed = sum(1 for v in self.results.values() if v)
        return {
            "total": total,
            "passed": passed,
            "failed": total - passed,
        }
