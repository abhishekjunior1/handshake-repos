"""Task command executor with retry support and environment management.

Executes task commands sequentially in a subprocess shell. Supports
variable expansion, environment capture from stdout, and configurable
retry policies for transient failures.
"""

import os
import subprocess
import logging
import time
import re

from config import SHELL, MAX_RETRIES, RETRY_DELAY, COMMAND_TIMEOUT

logger = logging.getLogger("taskrunner.executor")


class TaskExecutor:
    """Executes task commands with retry and environment management.

    Commands are run sequentially in a shell subprocess. Environment
    variables can be captured from command stdout using 'export KEY=VALUE'
    format. Failed commands trigger retries with environment reset to
    ensure clean retry state.
    """

    def __init__(self, workdir=None):
        self.workdir = workdir or os.getcwd()
        self.results = {}
        self.execution_log = []

    def execute_task(self, task, retry_count=None):
        """Execute all commands for a task.

        If the task has retries configured, uses the retry-aware
        execution path which resets state between attempts.
        """
        task_workdir = task.workdir or self.workdir
        env = self._build_env(task)
        retries = retry_count if retry_count is not None else task.retries
        if retries > 0:
            return self._execute_with_retry(task, task_workdir, env, retries)
        return self._execute_commands(task, task_workdir, env)

    def _execute_commands(self, task, workdir, env):
        """Execute commands sequentially, stopping on first failure."""
        results = []
        for i, command in enumerate(task.commands):
            expanded = self._expand_variables(command, env)
            result = self._run_command(expanded, workdir, env)
            results.append(result)
            if result["exit_code"] != 0:
                logger.error(
                    f"Task '{task.name}' failed at command {i}: {command}"
                )
                self.results[task.name] = {
                    "status": "failed",
                    "commands": results,
                    "exit_code": result["exit_code"],
                    "failed_at": i,
                }
                self._log_execution(task.name, "failed", len(results))
                return self.results[task.name]
            self._capture_env_exports(result, env)
        self.results[task.name] = {
            "status": "success",
            "commands": results,
            "exit_code": 0,
        }
        self._log_execution(task.name, "success", len(results))
        return self.results[task.name]

    def _execute_with_retry(self, task, workdir, env, max_retries):
        """Execute commands with retry on failure.

        On failure, resets the environment to the task-defined state
        and retries the failed command. This ensures each retry attempt
        starts from a known-good configuration baseline.
        """
        task_workdir = workdir
        results = []
        i = 0
        attempts_at_command = 0
        while i < len(task.commands):
            command = task.commands[i]
            expanded = self._expand_variables(command, env)
            result = self._run_command(expanded, task_workdir, env)
            results.append(result)
            if result["exit_code"] != 0:
                attempts_at_command += 1
                if attempts_at_command > max_retries:
                    logger.error(
                        f"Task '{task.name}' failed at command {i} after "
                        f"{max_retries} retries"
                    )
                    self.results[task.name] = {
                        "status": "failed",
                        "commands": results,
                        "exit_code": result["exit_code"],
                        "failed_at": i,
                    }
                    self._log_execution(task.name, "failed", len(results))
                    return self.results[task.name]
                logger.info(
                    f"Command {i} of task '{task.name}' failed, "
                    f"retry {attempts_at_command}/{max_retries}"
                )
                time.sleep(RETRY_DELAY)
                env = self._build_env(task)
                continue
            self._capture_env_exports(result, env)
            i += 1
            attempts_at_command = 0
        self.results[task.name] = {
            "status": "success",
            "commands": results,
            "exit_code": 0,
        }
        self._log_execution(task.name, "success", len(results))
        return self.results[task.name]

    def _build_env(self, task):
        """Build the execution environment from base OS env and task config."""
        env = dict(os.environ)
        for key, value in task.env.items():
            env[key] = self._expand_variables(value, env)
        return env

    def _expand_variables(self, command, env):
        """Expand environment variable references in a command string.

        Handles ${VAR} brace-delimited references first, then processes
        bare $VAR references found in the command template.
        """
        result = command
        pattern = r'\$\{([^}]+)\}'
        matches = re.findall(pattern, result)
        for var_name in matches:
            value = env.get(var_name, "")
            result = result.replace(f"${{{var_name}}}", value)
        simple_pattern = r'\$([A-Z_][A-Z0-9_]*)'
        for match in re.finditer(simple_pattern, command):
            var_name = match.group(1)
            if var_name in env:
                result = result.replace(f"${var_name}", env[var_name])
        return result

    def _run_command(self, command, workdir, env):
        """Execute a single command in a subprocess."""
        try:
            proc = subprocess.run(
                command,
                shell=True,
                executable=SHELL,
                cwd=workdir,
                env=env,
                capture_output=True,
                text=True,
                timeout=COMMAND_TIMEOUT,
            )
            return {
                "command": command,
                "exit_code": proc.returncode,
                "stdout": proc.stdout.strip(),
                "stderr": proc.stderr.strip(),
            }
        except subprocess.TimeoutExpired:
            logger.warning(f"Command timed out: {command}")
            return {
                "command": command,
                "exit_code": -1,
                "stdout": "",
                "stderr": "Command timed out",
            }
        except OSError as e:
            logger.error(f"OS error running command: {e}")
            return {
                "command": command,
                "exit_code": -2,
                "stdout": "",
                "stderr": str(e),
            }

    def _capture_env_exports(self, result, env):
        """Capture environment exports from command stdout.

        Commands can export variables by printing lines in the format:
        export KEY=VALUE
        These are captured into the execution environment for
        subsequent commands.
        """
        stdout = result.get("stdout", "")
        for line in stdout.split("\n"):
            line = line.strip()
            if line.startswith("export "):
                parts = line[7:].split("=", 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip().strip("'").strip('"')
                    env[key] = value

    def _log_execution(self, task_name, status, command_count):
        """Record task execution in the internal log."""
        self.execution_log.append({
            "task": task_name,
            "status": status,
            "commands_run": command_count,
            "timestamp": time.time(),
        })

    def get_result(self, task_name):
        """Get the execution result for a specific task."""
        return self.results.get(task_name)

    def get_all_results(self):
        """Get all task execution results."""
        return dict(self.results)

    def get_execution_log(self):
        """Get the full execution log."""
        return list(self.execution_log)

    def reset(self):
        """Reset executor state for fresh execution."""
        self.results = {}
        self.execution_log = []

    def get_task_duration(self, task_name):
        """Estimate task duration from log entries."""
        log_entries = [e for e in self.execution_log if e["task"] == task_name]
        if len(log_entries) < 1:
            return 0
        return log_entries[-1].get("timestamp", 0) - log_entries[0].get("timestamp", 0)
