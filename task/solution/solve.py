"""Oracle solution: fixes all three bugs in the task execution system."""

import subprocess
import sys


def fix_executor_expansion():
    """Fix Bug 1: Variable expansion second pass must search expanded result.

    The $VAR expansion pass must iterate over the partially-expanded result
    (after ${VAR} processing), not the original command text. Otherwise,
    $VAR references that appear only after ${VAR} expansion are missed.
    """
    path = "/app/executor.py"
    with open(path, "r") as f:
        content = f.read()

    old = """        simple_pattern = r'\\$([A-Z_][A-Z0-9_]*)'
        for match in re.finditer(simple_pattern, command):
            var_name = match.group(1)
            if var_name in env:
                result = result.replace(f"${var_name}", env[var_name])"""

    new = """        simple_pattern = r'\\$([A-Z_][A-Z0-9_]*)'
        for match in re.finditer(simple_pattern, result):
            var_name = match.group(1)
            if var_name in env:
                result = result.replace(f"${var_name}", env[var_name])"""

    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)


def fix_runner_ordering():
    """Fix Bug 2: Collect parallel results in submission order, not completion order.

    Using as_completed returns results in non-deterministic order based on
    execution time. The output must reflect the submission order for
    deterministic tasks_executed ordering.
    """
    path = "/app/runner.py"
    with open(path, "r") as f:
        content = f.read()

    old = """    def _execute_group(self, tasks, group_names, parallelism):
        \"\"\"Execute a group of tasks concurrently.

        Submits all group tasks to a thread pool and collects results
        as they complete for efficient resource utilization.
        \"\"\"
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
        return results"""

    new = """    def _execute_group(self, tasks, group_names, parallelism):
        \"\"\"Execute a group of tasks concurrently.

        Submits all group tasks to a thread pool and collects results
        in submission order for deterministic execution ordering.
        \"\"\"
        results = []
        with ThreadPoolExecutor(max_workers=parallelism) as pool:
            futures = []
            for task_name in group_names:
                task = tasks[task_name]
                future = pool.submit(self._execute_single, task)
                futures.append((task_name, future))
            for task_name, future in futures:
                result = future.result()
                results.append((task_name, result))
        return results"""

    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)


def fix_executor_retry():
    """Fix Bug 3: Remove env rebuild on retry to preserve captured state.

    When a command fails and triggers a retry, the accumulated environment
    (including exports from previous successful commands) must be preserved.
    Rebuilding from task.env loses captured state.
    """
    path = "/app/executor.py"
    with open(path, "r") as f:
        content = f.read()

    old = """                time.sleep(RETRY_DELAY)
                env = self._build_env(task)
                continue"""

    new = """                time.sleep(RETRY_DELAY)
                continue"""

    content = content.replace(old, new)
    with open(path, "w") as f:
        f.write(content)


def run_pipeline():
    """Run the pipeline to generate output."""
    result = subprocess.run(
        [sys.executable, "/app/runner.py", "/app/eval_taskfile.json", "/app/output_eval.json"],
        cwd="/app",
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Pipeline completed successfully")


def main():
    fix_executor_expansion()
    fix_runner_ordering()
    fix_executor_retry()
    run_pipeline()


if __name__ == "__main__":
    main()
