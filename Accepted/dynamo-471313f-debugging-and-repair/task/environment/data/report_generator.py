"""
Report generator for the work-stealing scheduler simulator.

Formats simulation results into structured output containing:
  - Execution trace (per-task timing and worker assignment)
  - Scheduling metrics (makespan, utilization, steal statistics)
  - Task completion order
  - Dependency resolution timeline
"""

import json
from typing import Any


class SimulationReport:
    """Assembles and formats the complete simulation report."""

    def __init__(self):
        self.execution_trace: list[dict] = []
        self.completion_order: list[str] = []
        self.scheduling_metrics: dict = {}
        self.worker_statistics: dict = {}
        self.steal_statistics: dict = {}
        self.dependency_timeline: list[dict] = []

    def add_task_execution(self, task_id: str, worker_id: int,
                           start_time: int, finish_time: int,
                           execution_cost: int, stolen: bool,
                           critical_path_length: float) -> None:
        """Record a task's execution details in the trace."""
        self.execution_trace.append({
            "task_id": task_id,
            "worker_id": worker_id,
            "start_time": start_time,
            "finish_time": finish_time,
            "execution_cost": execution_cost,
            "stolen": stolen,
            "critical_path_length": round(critical_path_length, 6)
        })

    def set_completion_order(self, order: list[str]) -> None:
        """Set the task completion order."""
        self.completion_order = list(order)

    def set_scheduling_metrics(self, makespan: int, total_tasks: int,
                               total_ticks: int, critical_path: float,
                               num_workers: int) -> None:
        """Set overall scheduling metrics."""
        speedup = 0.0
        if makespan > 0:
            total_work = sum(e["execution_cost"] for e in self.execution_trace)
            speedup = total_work / makespan
        efficiency = 0.0
        if total_ticks > 0 and num_workers > 0:
            total_exec = sum(
                w["execution_ticks"]
                for w in self.worker_statistics.get("per_worker", [])
            )
            efficiency = total_exec / (num_workers * total_ticks)

        self.scheduling_metrics = {
            "makespan": makespan,
            "total_tasks": total_tasks,
            "total_simulation_ticks": total_ticks,
            "critical_path_length": round(critical_path, 6),
            "speedup": round(speedup, 6),
            "efficiency": round(efficiency, 6)
        }

    def set_worker_statistics(self, stats: dict) -> None:
        """Set per-worker statistics."""
        self.worker_statistics = stats

    def set_steal_statistics(self, stats: dict) -> None:
        """Set steal protocol statistics."""
        self.steal_statistics = stats

    def add_dependency_event(self, tick: int, task_id: str,
                             released_by: str) -> None:
        """Record a dependency resolution event."""
        self.dependency_timeline.append({
            "tick": tick,
            "task_id": task_id,
            "released_by": released_by
        })

    def generate(self) -> dict:
        """Generate the complete report as a dictionary."""
        # Sort execution trace by start_time, then task_id for determinism
        self.execution_trace.sort(key=lambda x: (x["start_time"], x["task_id"]))

        report = {
            "execution_trace": self.execution_trace,
            "completion_order": self.completion_order,
            "scheduling_metrics": self.scheduling_metrics,
            "worker_statistics": self.worker_statistics,
            "steal_statistics": self.steal_statistics,
            "dependency_timeline": self.dependency_timeline
        }
        return report


def write_report(report: dict, output_path: str) -> None:
    """Write the simulation report to a JSON file."""
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)


def format_summary(report: dict) -> str:
    """Format a human-readable summary of the simulation."""
    metrics = report.get("scheduling_metrics", {})
    lines = [
        f"Makespan: {metrics.get('makespan', 0)} ticks",
        f"Tasks: {metrics.get('total_tasks', 0)}",
        f"Speedup: {metrics.get('speedup', 0.0):.3f}x",
        f"Efficiency: {metrics.get('efficiency', 0.0):.1%}",
        f"Critical Path: {metrics.get('critical_path_length', 0.0):.1f}",
        f"Steals: {report.get('steal_statistics', {}).get('total_successes', 0)}",
    ]
    return "\n".join(lines)
