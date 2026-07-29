"""
Window aggregation module. Computes per-key statistics with temporal
decay weighting for a single window's events.

Events are expected in chronological order so that decay weighting
assigns higher weights to more recent events within the window.
"""

import math


def compute_window_aggregation(events, decay_factor, baseline):
    """
    Compute aggregation statistics for a window's events.

    Produces per-key counts, sums, min/max, and a decay-weighted
    running sum. The baseline from previous windows is incorporated
    into the running sum computation.

    Events must be sorted by timestamp (chronological) for correct
    decay weighting — earlier events receive more decay, later events
    receive less.

    Parameters
    ----------
    events : list of dict
        Events sorted chronologically within the window.
    decay_factor : float
        Per-step temporal decay (0 < factor <= 1).
    baseline : float
        Carry-forward baseline from previous windows.

    Returns
    -------
    dict
        Aggregation result with per-key stats and window totals.
    """
    key_stats = {}
    window_sum = 0.0
    running_sum = baseline

    for i, event in enumerate(events):
        key = event["key"]
        value = event["value"]
        window_sum += value

        # Decay weight: more recent events (higher index) get higher weight
        # weight = decay_factor^(n - 1 - i) where n = total events
        # Applied after all events are seen (deferred weighting)
        if key not in key_stats:
            key_stats[key] = {
                "values": [],
                "count": 0,
                "sum": 0.0,
                "min": value,
                "max": value,
            }

        stats = key_stats[key]
        stats["values"].append(value)
        stats["count"] += 1
        stats["sum"] += value
        stats["min"] = min(stats["min"], value)
        stats["max"] = max(stats["max"], value)

    # Compute decay-weighted sums per key
    n_total = len(events)
    for key, stats in key_stats.items():
        values = stats["values"]
        n = len(values)
        weighted_sum = 0.0
        for i, v in enumerate(values):
            # Weight increases with position (later = more weight)
            weight = decay_factor ** (n - 1 - i)
            weighted_sum += v * weight
        stats["weighted_sum"] = weighted_sum
        stats["avg"] = stats["sum"] / stats["count"] if stats["count"] > 0 else 0.0
        del stats["values"]  # Don't carry raw values in output

    # Running sum incorporates baseline + window contribution
    running_sum = baseline * decay_factor + window_sum

    return {
        "key_stats": key_stats,
        "window_sum": round(window_sum, 6),
        "running_sum": round(running_sum, 6),
        "event_count": n_total,
    }
