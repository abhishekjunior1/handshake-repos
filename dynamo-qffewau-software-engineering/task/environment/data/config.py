"""Configuration constants and utility functions for the task runner.

Provides shared configuration values, file I/O helpers, and logging
setup used across all modules.
"""

import os
import json
import logging
import time
from pathlib import Path


DEFAULT_TASKFILE = "taskfile.json"
DEFAULT_OUTPUT = "/app/output.json"
DEFAULT_WORKDIR = "/app"
MAX_RETRIES = 3
RETRY_DELAY = 0.1
SHELL = "/bin/sh"
DEFAULT_PARALLELISM = 1
COMMAND_TIMEOUT = 300
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_LEVEL = logging.INFO


def setup_logging(level=None):
    """Configure logging for the task runner."""
    logging.basicConfig(
        format=LOG_FORMAT,
        level=level or LOG_LEVEL,
    )
    return logging.getLogger("taskrunner")


def resolve_path(path, base=None):
    """Resolve a path relative to a base directory."""
    if os.path.isabs(path):
        return path
    base = base or os.getcwd()
    return os.path.normpath(os.path.join(base, path))


def load_json(filepath):
    """Load and parse a JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def write_json(filepath, data):
    """Write data to a JSON file, creating directories as needed."""
    os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
    with open(filepath, "w") as f:
        json.dump(data, f, indent=2)


def get_env_or_default(key, default=None):
    """Get an environment variable with a default fallback."""
    return os.environ.get(key, default)


def validate_file_exists(path):
    """Validate that a file exists, raising FileNotFoundError if not."""
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Required file not found: {path}")
    return True


def merge_dicts(base, override):
    """Merge two dictionaries with override taking precedence."""
    result = dict(base)
    result.update(override)
    return result


def elapsed_ms(start):
    """Calculate elapsed time in milliseconds since start."""
    return round((time.time() - start) * 1000, 2)


def ensure_directory(path):
    """Ensure a directory exists, creating it if necessary."""
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def sanitize_name(name):
    """Sanitize a task name for use in file paths."""
    return name.replace(" ", "-").replace("/", "_").lower()
