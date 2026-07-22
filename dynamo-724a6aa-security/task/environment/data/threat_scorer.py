"""
Threat Scoring Engine

Computes threat scores for IP addresses based on their event history.
Supports raw aggregation and temporal decay models. The decay formula
uses exponential half-life to reduce the contribution of older events,
reflecting the diminishing relevance of historical observations.
"""

import math
import copy
from typing import Any


def compute_raw_score(events: list[dict[str, Any]]) -> float:
    """
    Compute the raw threat score as the sum of all severity values.

    This method treats all events equally regardless of when they occurred.
    Suitable for short observation windows where temporal relevance is uniform.

    Args:
        events: List of security events with 'severity' field.

    Returns:
        Sum of all severity values as a float.
    """
    total = 0.0
    for event in events:
        severity = event.get('severity', 0)
        total += float(severity)
    return total


def apply_temporal_decay(events: list[dict[str, Any]],
                         reference_time: float,
                         half_life_seconds: float) -> list[dict[str, Any]]:
    """
    Apply temporal decay to event severities based on their age.

    Uses the formula: decayed_severity = severity * 2^(-(reference_time - event_time) / half_life)

    Events closer to the reference time retain more of their original severity,
    while older events have their severity reduced exponentially.

    Args:
        events: List of security events with 'severity' and 'timestamp' fields.
        reference_time: The reference timestamp (typically current time or analysis time).
        half_life_seconds: Time in seconds for severity to decay to half its value.

    Returns:
        New list of events with 'decayed_severity' field added to each.
    """
    decayed_events = []

    for event in events:
        decayed_event = copy.deepcopy(event)
        event_time = float(event.get('timestamp', 0))
        severity = float(event.get('severity', 0))

        # Compute time delta (age of event)
        age_seconds = reference_time - event_time

        # Apply exponential decay: severity * 2^(-age/half_life)
        if half_life_seconds > 0 and age_seconds >= 0:
            decay_factor = math.pow(2, -(age_seconds / half_life_seconds))
        elif age_seconds < 0:
            # Future events get no decay
            decay_factor = 1.0
        else:
            decay_factor = 0.0

        decayed_severity = severity * decay_factor
        decayed_event['decayed_severity'] = decayed_severity
        decayed_event['decay_factor'] = decay_factor
        decayed_events.append(decayed_event)

    return decayed_events


def compute_decayed_score(events: list[dict[str, Any]],
                          reference_time: float,
                          half_life_seconds: float) -> float:
    """
    Compute the threat score with temporal decay applied.

    Applies the decay formula to each event's severity and returns the sum
    of decayed severities. This gives more weight to recent events and
    reduces the impact of stale observations.

    Args:
        events: List of security events with 'severity' and 'timestamp' fields.
        reference_time: The reference timestamp for decay calculation.
        half_life_seconds: Time in seconds for severity to decay to half its value.

    Returns:
        Sum of all decayed severity values as a float.
    """
    decayed_events = apply_temporal_decay(events, reference_time, half_life_seconds)

    total = 0.0
    for event in decayed_events:
        total += event.get('decayed_severity', 0.0)

    return total


def normalize_score(raw_score: float, max_possible: float) -> float:
    """
    Normalize a threat score to the 0-1 range.

    Args:
        raw_score: The raw or decayed threat score.
        max_possible: The maximum possible score for normalization.

    Returns:
        Normalized score between 0.0 and 1.0.
    """
    if max_possible <= 0:
        return 0.0

    normalized = raw_score / max_possible

    # Clamp to [0, 1]
    return max(0.0, min(1.0, normalized))
