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


def fix_runner_group_ordering():
    """Fix Bug 2: Use alphabetical group ordering, not priority-based.

    The runner uses get_scheduled_groups() which orders tasks by priority
    within each level. The correct function is get_parallelizable_groups()
    which uses alphabetical ordering for deterministic output that matches
    the expected task execution sequence.
    """
    path = "/app/runner.py"
    with open(path, "r") as f:
        content = f.read()

    old = "        groups = resolver.get_scheduled_groups()"
    new = "        groups = resolver.get_parallelizable_groups()"

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
        [sys.executable, "/app/runner.py", "/app/taskfile.json", "/app/output.json"],
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
    fix_runner_group_ordering()
    fix_executor_retry()
    run_pipeline()


if __name__ == "__main__":
    main()
