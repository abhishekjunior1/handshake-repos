"""
Event processor for the deterministic scheduler simulation.

Manages the simulation event loop: processes events in tick order,
handles task completions, steal events, and scheduling decisions.
The simulation is fully deterministic — given the same input DAG and
configuration, it always produces the same execution trace.
"""

from typing import Optional
from task_queue import TaskDescriptor


class SimulationEvent:
    """Represents a discrete event in the simulation."""

    TASK_COMPLETE = "task_complete"
    TASK_START = "task_start"
    STEAL_ATTEMPT = "steal_attempt"
    STEAL_SUCCESS = "steal_success"
    STEAL_FAILURE = "steal_failure"
    TASK_READY = "task_ready"
    WORKER_IDLE = "worker_idle"

    def __init__(self, tick: int, event_type: str, worker_id: int,
                 task_id: Optional[str] = None, details: Optional[dict] = None):
        self.tick = tick
        self.event_type = event_type
        self.worker_id = worker_id
        self.task_id = task_id
        self.details = details or {}

    def to_dict(self) -> dict:
        """Convert event to dictionary for trace output."""
        result = {
            "tick": self.tick,
            "event": self.event_type,
            "worker": self.worker_id
        }
        if self.task_id:
            result["task"] = self.task_id
        if self.details:
            result.update(self.details)
        return result


class EventLog:
    """Maintains an ordered log of simulation events."""

    def __init__(self):
        self._events: list[SimulationEvent] = []

    def record(self, event: SimulationEvent) -> None:
        """Append an event to the log."""
        self._events.append(event)

    def record_task_start(self, tick: int, worker_id: int, task_id: str,
                          stolen: bool = False) -> None:
        """Log a task starting execution."""
        details = {"stolen": stolen}
        self.record(SimulationEvent(
            tick, SimulationEvent.TASK_START, worker_id, task_id, details
        ))

    def record_task_complete(self, tick: int, worker_id: int, task_id: str,
                             execution_cost: int) -> None:
        """Log a task completing execution."""
        details = {"execution_cost": execution_cost}
        self.record(SimulationEvent(
            tick, SimulationEvent.TASK_COMPLETE, worker_id, task_id, details
        ))

    def record_steal(self, tick: int, thief_id: int, victim_id: int,
                     task_id: Optional[str], success: bool) -> None:
        """Log a steal attempt (success or failure)."""
        event_type = (SimulationEvent.STEAL_SUCCESS if success
                      else SimulationEvent.STEAL_FAILURE)
        details = {"victim": victim_id}
        self.record(SimulationEvent(
            tick, event_type, thief_id, task_id, details
        ))

    def record_task_ready(self, tick: int, task_id: str) -> None:
        """Log a task becoming ready (all deps satisfied)."""
        self.record(SimulationEvent(
            tick, SimulationEvent.TASK_READY, -1, task_id
        ))

    def get_trace(self) -> list[dict]:
        """Return the full event trace as list of dicts."""
        return [e.to_dict() for e in self._events]

    def get_events_at_tick(self, tick: int) -> list[SimulationEvent]:
        """Get all events that occurred at a specific tick."""
        return [e for e in self._events if e.tick == tick]

    def get_task_events(self, task_id: str) -> list[SimulationEvent]:
        """Get all events related to a specific task."""
        return [e for e in self._events if e.task_id == task_id]

    def get_completion_events(self) -> list[SimulationEvent]:
        """Get all task completion events in order."""
        return [e for e in self._events
                if e.event_type == SimulationEvent.TASK_COMPLETE]

    def count_events(self, event_type: str) -> int:
        """Count events of a specific type."""
        return sum(1 for e in self._events if e.event_type == event_type)


class TickSimulator:
    """Drives the discrete-time simulation forward tick by tick.

    Each tick processes:
    1. Task completions (tasks that finish this tick)
    2. Dependency resolution (newly ready tasks)
    3. Work assignment (ready tasks → idle workers)
    4. Work stealing (idle workers steal from busy ones)
    """

    def __init__(self, max_ticks: int = 10000):
        self.max_ticks = max_ticks
        self.current_tick = 0
        self.event_log = EventLog()

    def advance_tick(self) -> int:
        """Advance simulation by one tick. Returns new tick value."""
        self.current_tick += 1
        return self.current_tick

    def is_simulation_complete(self, total_tasks: int,
                               completed_count: int) -> bool:
        """Check if simulation should terminate."""
        if completed_count >= total_tasks:
            return True
        if self.current_tick >= self.max_ticks:
            return True
        return False

    def get_current_tick(self) -> int:
        """Return current simulation tick."""
        return self.current_tick

    def get_event_log(self) -> EventLog:
        """Return the event log."""
        return self.event_log

    def get_simulation_stats(self) -> dict:
        """Return simulation timing statistics."""
        return {
            "total_ticks": self.current_tick,
            "task_starts": self.event_log.count_events(SimulationEvent.TASK_START),
            "task_completions": self.event_log.count_events(SimulationEvent.TASK_COMPLETE),
            "steal_successes": self.event_log.count_events(SimulationEvent.STEAL_SUCCESS),
            "steal_failures": self.event_log.count_events(SimulationEvent.STEAL_FAILURE)
        }
