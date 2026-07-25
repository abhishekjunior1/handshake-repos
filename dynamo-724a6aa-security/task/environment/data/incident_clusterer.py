"""
Incident Clustering Engine

Clusters related security events into incidents based on temporal proximity
and source correlation. Uses geometric mean for severity aggregation, which
is the correct choice for values on a logarithmic scale (severity 1-10).
"""

import math
import uuid
from typing import Any
from collections import defaultdict


def cluster_by_source(events: list[dict[str, Any]],
                      time_window_sec: float) -> list[list[dict[str, Any]]]:
    """
    Group events from the same source IP into temporal clusters.

    Events from the same src_ip that occur within the specified time window
    are grouped into a single cluster. A new cluster begins when an event
    occurs more than time_window_sec after the previous event in that source's
    timeline.

    Args:
        events: List of security events sorted by source.
        time_window_sec: Maximum time gap (seconds) between events in a cluster.

    Returns:
        List of event clusters (each cluster is a list of events).
    """
    # Group events by source IP
    source_groups = defaultdict(list)
    for event in events:
        src_ip = event.get('src_ip', 'unknown')
        source_groups[src_ip].append(event)

    clusters = []

    for src_ip, src_events in source_groups.items():
        # Sort by timestamp
        sorted_events = sorted(src_events, key=lambda e: e.get('timestamp', 0))

        if not sorted_events:
            continue

        # Build clusters using time window
        current_cluster = [sorted_events[0]]

        for i in range(1, len(sorted_events)):
            current_time = sorted_events[i].get('timestamp', 0)
            prev_time = sorted_events[i - 1].get('timestamp', 0)

            if current_time - prev_time <= time_window_sec:
                current_cluster.append(sorted_events[i])
            else:
                clusters.append(current_cluster)
                current_cluster = [sorted_events[i]]

        # Add the last cluster
        clusters.append(current_cluster)

    return clusters


def compute_cluster_severity(events: list[dict[str, Any]],
                             aggregation: str = 'geometric_mean') -> float:
    """
    Compute the aggregate severity for a cluster of events.

    Uses geometric mean by default, which is the correct aggregation for
    severity values on a logarithmic scale. The geometric mean prevents
    a single high-severity event from dominating while still reflecting
    the overall threat level accurately.

    Args:
        events: List of events in the cluster.
        aggregation: Aggregation method ('geometric_mean' or 'arithmetic_mean').

    Returns:
        Aggregated severity value.
    """
    if not events:
        return 0.0

    severities = [float(e.get('severity', 1)) for e in events]

    if aggregation == 'geometric_mean':
        # Geometric mean: (product of values)^(1/n)
        # Use log-sum-exp for numerical stability
        n = len(severities)
        if n == 0:
            return 0.0

        log_sum = sum(math.log(max(s, 1e-10)) for s in severities)
        return math.exp(log_sum / n)

    elif aggregation == 'arithmetic_mean':
        return sum(severities) / len(severities)

    else:
        raise ValueError(f"Unknown aggregation method: {aggregation}")


def create_incident(cluster: list[dict[str, Any]], severity: float) -> dict[str, Any]:
    """
    Create a structured incident record from a cluster of events.

    Args:
        cluster: List of events forming the incident.
        severity: Computed aggregate severity for the cluster.

    Returns:
        Incident dictionary with metadata, severity, and event references.
    """
    if not cluster:
        return {}

    # Extract metadata from cluster
    timestamps = [e.get('timestamp', 0) for e in cluster]
    src_ips = list(set(e.get('src_ip', '') for e in cluster))
    dest_ips = list(set(e.get('dest_ip', '') for e in cluster))
    rule_ids = list(set(e.get('rule_id', '') for e in cluster))
    event_types = list(set(e.get('event_type', '') for e in cluster))

    incident = {
        'incident_id': str(uuid.uuid4()),
        'start_time': min(timestamps),
        'end_time': max(timestamps),
        'duration_sec': max(timestamps) - min(timestamps),
        'severity': severity,
        'event_count': len(cluster),
        'source_ips': sorted(src_ips),
        'destination_ips': sorted(dest_ips),
        'rule_ids': sorted(rule_ids),
        'event_types': sorted(event_types),
        'event_ids': [e.get('event_id', '') for e in cluster]
    }

    return incident
