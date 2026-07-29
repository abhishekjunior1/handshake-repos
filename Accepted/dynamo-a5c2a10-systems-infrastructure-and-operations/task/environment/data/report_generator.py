"""
Report generator for task queue processing results.

Formats processing outcomes into structured JSON output including
processing log, task outcomes, DLQ contents, consumer stats, and summary.
"""

import json
from typing import Any


class ReportGenerator:
    """
    Generates formatted output reports for task queue processing runs.

    Collects events during processing and produces the final structured
    output containing all processing details and metrics.
    """

    def __init__(self):
        self._processing_log: list[dict] = []
        self._task_outcomes: dict[str, dict] = {}
        self._dlq_contents: list[dict] = []
        self._consumer_stats: dict[str, dict] = {}
        self._summary: dict[str, Any] = {}

    def log_event(self, tick: int, event_type: str, task_id: str,
                  consumer_id: str = "", details: str = "") -> None:
        """Record a processing event in chronological order."""
        entry = {
            "tick": tick,
            "event": event_type,
            "task_id": task_id,
            "consumer_id": consumer_id,
            "details": details,
        }
        self._processing_log.append(entry)

    def record_task_outcome(self, task_id: str, status: str, retries_used: int,
                            final_consumer: str, completed_at_tick: int) -> None:
        """Record the final outcome of a task."""
        self._task_outcomes[task_id] = {
            "task_id": task_id,
            "status": status,
            "retries_used": retries_used,
            "final_consumer": final_consumer,
            "completed_at_tick": completed_at_tick,
        }

    def set_dlq_contents(self, contents: list[dict]) -> None:
        """Set dead letter queue contents for the report."""
        self._dlq_contents = contents

    def set_consumer_stats(self, stats: dict) -> None:
        """Set per-consumer statistics."""
        self._consumer_stats = stats

    def set_summary(self, total_tasks: int, completed: int, failed: int,
                    dlq_count: int, total_ticks: int) -> None:
        """Set the processing summary."""
        self._summary = {
            "total_tasks": total_tasks,
            "completed": completed,
            "failed": failed,
            "dead_lettered": dlq_count,
            "total_ticks": total_ticks,
        }

    def generate_report(self) -> dict:
        """Generate the complete processing report."""
        return {
            "processing_log": self._processing_log,
            "task_outcomes": self._task_outcomes,
            "dlq_contents": self._dlq_contents,
            "consumer_stats": self._consumer_stats,
            "summary": self._summary,
        }

    def write_report(self, filepath: str) -> None:
        """Write the report to a JSON file."""
        report = self.generate_report()
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)

    def get_event_count(self) -> int:
        return len(self._processing_log)

    def get_events_by_type(self, event_type: str) -> list[dict]:
        return [e for e in self._processing_log if e["event"] == event_type]

    def get_task_outcome(self, task_id: str) -> dict:
        return self._task_outcomes.get(task_id, {})
