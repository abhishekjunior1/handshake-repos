"""
Window trigger evaluation for streaming processing.

Determines when accumulated window results should be emitted based on
watermark advancement past window boundaries. A window fires when the
watermark passes the window's end timestamp, indicating that no more
on-time events for that window are expected.
"""

from typing import Any


class TriggerState:
    """Tracks which windows have been triggered for emission."""

    def __init__(self):
        self.triggered_windows: set[str] = set()
        self.pending_windows: set[str] = set()
        self.trigger_history: list[dict[str, Any]] = []

    def to_dict(self) -> dict[str, Any]:
        """Serialize trigger state."""
        return {
            "triggered_count": len(self.triggered_windows),
            "pending_count": len(self.pending_windows),
            "trigger_history": self.trigger_history
        }


def initialize_trigger_state() -> TriggerState:
    """Create fresh trigger evaluation state."""
    return TriggerState()


def register_window(state: TriggerState, window_key: str) -> None:
    """Register a window as pending (awaiting trigger condition)."""
    if window_key not in state.triggered_windows:
        state.pending_windows.add(window_key)


def evaluate_triggers(
    state: TriggerState,
    watermark: float,
    window_boundaries: dict[str, float]
) -> list[str]:
    """Evaluate which pending windows should fire based on current watermark.

    A window fires when the watermark passes the window's end timestamp.
    The window_boundaries dict maps window_key -> trigger_timestamp (the
    timestamp that the watermark must pass for the window to fire).

    Returns list of window keys that should fire in this evaluation cycle.
    """
    newly_triggered = []

    for window_key in list(state.pending_windows):
        trigger_ts = window_boundaries.get(window_key)
        if trigger_ts is None:
            continue

        # Window fires when watermark passes its trigger timestamp
        if watermark >= trigger_ts:
            newly_triggered.append(window_key)
            state.pending_windows.discard(window_key)
            state.triggered_windows.add(window_key)
            state.trigger_history.append({
                "window_key": window_key,
                "trigger_timestamp": trigger_ts,
                "watermark_at_trigger": watermark
            })

    # Sort for deterministic emission order
    newly_triggered.sort()
    return newly_triggered


def get_trigger_timestamp(window_end: float) -> float:
    """Compute the trigger timestamp for a window.

    For event-time processing with watermarks, a window triggers when the
    watermark passes the window's end boundary. The trigger timestamp is
    the window's end timestamp.
    """
    return window_end


def compute_trigger_delay(
    trigger_history: list[dict[str, Any]],
    window_spans: dict[str, dict[str, float]]
) -> dict[str, float]:
    """Compute triggering delay for each triggered window.

    Delay is measured as: watermark_at_trigger - window_end.
    A delay of 0 means the window fired exactly when expected.
    """
    delays = {}
    for entry in trigger_history:
        window_key = entry["window_key"]
        if window_key in window_spans:
            window_end = window_spans[window_key]["end"]
            delays[window_key] = entry["watermark_at_trigger"] - window_end
    return delays


def is_window_triggered(state: TriggerState, window_key: str) -> bool:
    """Check if a specific window has already been triggered."""
    return window_key in state.triggered_windows
