"""CDC Event Deduplication Engine.

Handles deduplication of CDC events using last-writer-wins semantics
within duplicate groups. For CDC streams, duplicate events are those
with the same primary key arriving within a deduplication window
(representing network retries or connector replays). The most recent
event per deduplication key represents the authoritative state.
"""


DEDUP_WINDOW_MS = 10000  # 10-second window for duplicate detection


def deduplicate_events(events):
    """Deduplicate events by primary key within timestamp windows.

    Uses last-writer-wins (LWW) semantics within each dedup group:
    events sharing the same primary key AND falling within the
    deduplication window are considered duplicates. Only the event
    with the latest timestamp from each group is retained.

    This is the correct approach for CDC streams where connector
    replays and network retries produce duplicate events with
    near-identical timestamps for the same primary key.

    Args:
        events: List of CDCEvent objects to deduplicate.

    Returns:
        Tuple of (deduplicated_events, dedup_stats) where dedup_stats
        contains metrics about the deduplication process.
    """
    if not events:
        return [], _empty_stats()

    sorted_events = sorted(events, key=lambda e: (e.table_name,
                                                   _pk_str(e.primary_key),
                                                   e.timestamp))

    groups = _identify_duplicate_groups(sorted_events)
    deduplicated = _resolve_groups(groups)
    deduplicated.sort(key=lambda e: e.timestamp)

    duplicates_removed = len(events) - len(deduplicated)
    stats = {
        "total_input_events": len(events),
        "deduplicated_count": len(deduplicated),
        "duplicates_removed": duplicates_removed,
        "dedup_ratio": round(duplicates_removed / len(events), 4) if events else 0.0
    }

    return deduplicated, stats


def _identify_duplicate_groups(sorted_events):
    """Identify groups of duplicate events by PK within time windows.

    Events with the same primary key (within the same table) that arrive
    within DEDUP_WINDOW_MS of each other are considered duplicates of the
    same source event.
    """
    groups = []
    current_group = [sorted_events[0]]

    for i in range(1, len(sorted_events)):
        event = sorted_events[i]
        prev = current_group[-1]

        same_table = event.table_name == prev.table_name
        same_pk = _pk_str(event.primary_key) == _pk_str(prev.primary_key)

        if same_table and same_pk:
            time_diff_ms = _timestamp_diff_ms(prev.timestamp, event.timestamp)
            if time_diff_ms <= DEDUP_WINDOW_MS:
                current_group.append(event)
            else:
                groups.append(current_group)
                current_group = [event]
        else:
            groups.append(current_group)
            current_group = [event]

    groups.append(current_group)
    return groups


def _resolve_groups(groups):
    """Resolve each duplicate group using last-writer-wins.

    For each group of duplicate events, keeps the event with the
    latest timestamp as the authoritative version.
    """
    resolved = []
    for group in groups:
        winner = max(group, key=lambda e: e.timestamp)
        resolved.append(winner)
    return resolved


def _timestamp_diff_ms(ts1, ts2):
    """Compute absolute time difference between two ISO timestamps in ms."""
    from datetime import datetime

    def parse_ts(ts):
        if ts.endswith("Z"):
            ts = ts[:-1] + "+00:00"
        return datetime.fromisoformat(ts)

    dt1 = parse_ts(ts1)
    dt2 = parse_ts(ts2)
    diff = abs((dt2 - dt1).total_seconds() * 1000)
    return diff


def _pk_str(pk):
    """Normalize primary key to string for comparison."""
    if isinstance(pk, dict):
        return "|".join(f"{k}={v}" for k, v in sorted(pk.items()))
    elif isinstance(pk, list):
        return "|".join(str(x) for x in pk)
    return str(pk)


def _empty_stats():
    """Return empty deduplication statistics."""
    return {
        "total_input_events": 0,
        "deduplicated_count": 0,
        "duplicates_removed": 0,
        "dedup_ratio": 0.0
    }
