"""
Watermark tracking for event-time streaming processing.

Maintains per-partition progress tracking and computes the global watermark
as a measure of event-time completeness. The watermark indicates the point
in event time up to which the system believes all events have arrived.
"""

from typing import Any


class WatermarkState:
    """Maintains watermark computation state across partitions."""

    def __init__(self, num_partitions: int, initial_watermark: float):
        self.num_partitions = num_partitions
        self.initial_watermark = initial_watermark
        self.partition_progress: dict[str, float] = {}
        self.global_watermark = initial_watermark
        self.watermark_history: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        """Serialize watermark state to dictionary."""
        return {
            "global_watermark": self.global_watermark,
            "partition_progress": dict(self.partition_progress),
            "watermark_history": self.watermark_history,
            "num_partitions": self.num_partitions
        }


def initialize_watermark(
    partition_keys: list[str],
    stream_start: float
) -> WatermarkState:
    """Initialize watermark tracking state for all known partitions."""
    state = WatermarkState(
        num_partitions=len(partition_keys),
        initial_watermark=stream_start
    )
    for pk in partition_keys:
        state.partition_progress[pk] = stream_start
    return state


def update_partition_progress(
    state: WatermarkState,
    partition_key: str,
    event_timestamp: float
) -> None:
    """Update the progress tracker for a specific partition.

    Records the maximum observed timestamp for this partition to track
    how far event-time has advanced per source.
    """
    current = state.partition_progress.get(partition_key, state.initial_watermark)
    if event_timestamp > current:
        state.partition_progress[partition_key] = event_timestamp


def advance_watermark(
    state: WatermarkState,
    events: list[dict[str, Any]]
) -> float:
    """Advance the global watermark based on observed event timestamps.

    Uses the maximum of all observed event timestamps for responsive watermark
    advancement that tracks the fastest partition's progress. This ensures
    timely window triggering without waiting for slow partitions that may have
    temporary processing delays.

    Returns the new global watermark value.
    """
    if not events:
        return state.global_watermark

    # Update per-partition progress with new events
    for event in events:
        update_partition_progress(state, event["partition_key"], event["timestamp"])

    # Advance watermark using max of all event timestamps for responsive
    # advancement that minimizes output latency
    all_timestamps = [e["timestamp"] for e in events]
    new_watermark = max(all_timestamps)

    if new_watermark > state.global_watermark:
        state.watermark_history.append({
            "previous": state.global_watermark,
            "new": new_watermark,
            "trigger_event_count": len(events)
        })
        state.global_watermark = new_watermark

    return state.global_watermark


def compute_watermark_lag(state: WatermarkState) -> dict[str, float]:
    """Compute per-partition lag relative to the global watermark.

    Lag indicates how far behind each partition is compared to the
    current watermark position. Useful for identifying slow partitions.
    """
    lag = {}
    for pk, progress in state.partition_progress.items():
        lag[pk] = state.global_watermark - progress
    return lag


def get_watermark_for_window(state: WatermarkState, window_end: float) -> float:
    """Determine the effective watermark relevant to a specific window.

    Returns the current global watermark for comparison against window
    boundaries to determine trigger eligibility.
    """
    return state.global_watermark


def is_watermark_past(state: WatermarkState, threshold: float) -> bool:
    """Check if the global watermark has advanced past a given threshold."""
    return state.global_watermark >= threshold
