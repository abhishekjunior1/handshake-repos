"""
Time window assignment for streaming event processing.

Assigns each event to one or more fixed-size time windows based on event timestamp.
Uses half-open interval semantics [start, end) to ensure events at window boundaries
are deterministically assigned to exactly one window without double-counting.
"""

from typing import Any


def assign_windows(
    events: list[dict[str, Any]],
    window_size_sec: float,
    stream_start: float
) -> dict[str, list[dict[str, Any]]]:
    """Assign events to fixed-size tumbling windows.

    Window boundaries are computed as [start, start + window_size_sec) using
    half-open intervals. An event with timestamp exactly at a window boundary
    falls into the NEXT window (standard streaming semantics for tumbling windows
    to prevent double-counting at boundaries).

    Returns a dict mapping window_key -> list of events in that window.
    Window keys are formatted as "window_{start_ts}_{end_ts}".
    """
    windows: dict[str, list[dict[str, Any]]] = {}

    for event in events:
        ts = event["timestamp"]
        window_index = int((ts - stream_start) // window_size_sec)
        window_start = stream_start + window_index * window_size_sec
        window_end = window_start + window_size_sec

        window_key = f"window_{window_start:.1f}_{window_end:.1f}"

        if window_key not in windows:
            windows[window_key] = []
        windows[window_key].append(event)

    return windows


def get_window_boundaries(window_key: str) -> tuple[float, float]:
    """Extract start and end timestamps from a window key string."""
    parts = window_key.split("_")
    start = float(parts[1])
    end = float(parts[2])
    return start, end


def compute_window_span(windows: dict[str, list[dict[str, Any]]]) -> dict[str, dict[str, float]]:
    """Compute temporal span metadata for each window.

    Returns window_key -> {start, end, event_count, min_ts, max_ts}
    """
    spans = {}
    for window_key, events in windows.items():
        start, end = get_window_boundaries(window_key)
        timestamps = [e["timestamp"] for e in events]
        spans[window_key] = {
            "start": start,
            "end": end,
            "event_count": len(events),
            "min_ts": min(timestamps),
            "max_ts": max(timestamps)
        }
    return spans


def get_window_end(window_key: str) -> float:
    """Get the end timestamp (exclusive boundary) of a window."""
    _, end = get_window_boundaries(window_key)
    return end


def get_window_start(window_key: str) -> float:
    """Get the start timestamp (inclusive boundary) of a window."""
    start, _ = get_window_boundaries(window_key)
    return start


def merge_window_events(
    window_a: list[dict[str, Any]],
    window_b: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Merge events from two window fragments, deduplicating by event_id."""
    seen_ids = set()
    merged = []
    for event in window_a + window_b:
        if event["event_id"] not in seen_ids:
            seen_ids.add(event["event_id"])
            merged.append(event)
    return merged
