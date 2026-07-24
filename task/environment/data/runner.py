"""Pipeline runner orchestrating task execution.

Coordinates sequential and parallel task execution based on the
configured parallelism level. Handles dependency resolution,
condition evaluation, and output generation.
"""

import sys
import os
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from config import setup_logging, write_json, DEFAULT_OUTPUT, elapsed_ms
from taskfile import TaskfileParser
from resolver import DependencyResolver, CyclicDependencyError
from executor import TaskExecutor
from condition import ConditionEvaluator

logger = logging.getLogger("taskrunner.runner")


class PipelineRunner:
    """Orchestrates task pipeline execution.

    Supports both sequential execution (parallelism=1) and parallel
    execution with configurable worker count. Tasks are scheduled
    respecting dependency ordering and priority within each level.
    """

    def __init__(self, taskfile_path, output_path=None, targets=None):
        self.taskfile_path = taskfile_path
        self.output_path = output_path or DEFAULT_OUTPUT
        self.targets = targets
        self.parser = TaskfileParser(taskfile_path)
        self.executor = TaskExecutor()
        self.evaluator = ConditionEvaluator()
        self.task_timings = {}

    def run(self):
        """Execute the full pipeline and write results."""
        start_time = time.time()
        logger.info(f"Loading taskfile: {self.taskfile_path}")
        tasks = self.parser.parse()
        self.parser.validate_dependencies()
        parallelism = self.parser.get_parallelism()
        resolver = DependencyResolver(tasks)
        try:
            order = resolver.resolve(self.targets)
        except CyclicDependencyError as e:
            logger.error(f"Dependency resolution failed: {e}")
            self._write_failure(str(e))
            return False
        logger.info(f"Execution order: {order}")
        logger.info(f"Parallelism: {parallelism}")
        if parallelism > 1:
            success, executed = self._run_parallel(tasks, resolver, parallelism)
        else:
            success, executed = self._run_sequential(tasks, order)
        duration = elapsed_ms(start_time)
        self._write_output(success, executed, duration)
        return success

    def _run_sequential(self, tasks, order):
        """Execute tasks one at a time in resolved order."""
        executed = []
        for task_name in order:
            task = tasks[task_name]
            if not self.evaluator.evaluate_preconditions(task):
                logger.info(f"Skipping task '{task_name}': preconditions not met")
                continue
            start = time.time()
            result = self.executor.execute_task(task)
            self.task_timings[task_name] = elapsed_ms(start)
            executed.append(task_name)
            if result["status"] != "success":
                logger.error(f"Task '{task_name}' failed")
                return False, executed
            if not self.evaluator.evaluate_postconditions(task):
                logger.error(f"Task '{task_name}' postconditions failed")
                return False, executed
        return True, executed

    def _run_parallel(self, tasks, resolver, parallelism):
        """Execute tasks in parallel groups respecting dependencies.

        Tasks within each group are submitted concurrently and results
        are collected as they complete for responsive error handling.
        """
        groups = resolver.get_parallelizable_groups()
        executed = []
        for group in groups:
            eligible = []
            for task_name in group:
                task = tasks[task_name]
                if self.evaluator.evaluate_preconditions(task):
                    eligible.append(task_name)
                else:
                    logger.info(
                        f"Skipping task '{task_name}': preconditions not met"
                    )
            if not eligible:
                continue
            group_results = self._execute_group(tasks, eligible, parallelism)
            for task_name, result in group_results:
                executed.append(task_name)
                if result["status"] != "success":
                    logger.error(f"Task '{task_name}' failed in parallel group")
                    return False, executed
                task = tasks[task_name]
                if not self.evaluator.evaluate_postconditions(task):
                    logger.error(
                        f"Task '{task_name}' postconditions failed"
                    )
                    return False, executed
        return True, executed

    def _execute_group(self, tasks, group_names, parallelism):
        """Execute a group of tasks concurrently.

        Submits all group tasks to a thread pool and collects results
        as they complete for efficient resource utilization.
        """
        results = []
        with ThreadPoolExecutor(max_workers=parallelism) as pool:
            future_map = {}
            for task_name in group_names:
                task = tasks[task_name]
                future = pool.submit(self._execute_single, task)
                future_map[future] = task_name
            for future in as_completed(future_map):
                task_name = future_map[future]
                result = future.result()
                results.append((task_name, result))
        return results

    def _execute_single(self, task):
        """Execute a single task in a thread-safe manner."""
        start = time.time()
        executor = TaskExecutor(workdir=self.executor.workdir)
        result = executor.execute_task(task)
        self.task_timings[task.name] = elapsed_ms(start)
        self.executor.results[task.name] = result
        return result

    def _write_output(self, success, executed, duration_ms):
        """Write pipeline execution results to output file."""
        output = {
            "success": success,
            "tasks_executed": executed,
            "results": self.executor.get_all_results(),
            "duration_ms": duration_ms,
            "timings": self.task_timings,
        }
        write_json(self.output_path, output)
        logger.info(f"Output written to {self.output_path} ({duration_ms}ms)")

    def _write_failure(self, error):
        """Write failure output when pipeline cannot start."""
        output = {
            "success": False,
            "error": error,
            "tasks_executed": [],
            "results": {},
            "duration_ms": 0,
            "timings": {},
        }
        write_json(self.output_path, output)

    def get_timings(self):
        """Get task execution timings."""
        return dict(self.task_timings)


def main():
    setup_logging()
    taskfile = sys.argv[1] if len(sys.argv) > 1 else "taskfile.json"
    output = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUTPUT
    targets = sys.argv[3:] if len(sys.argv) > 3 else None
    runner = PipelineRunner(taskfile, output, targets)
    success = runner.run()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
