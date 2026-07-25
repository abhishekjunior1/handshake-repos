"""SCD Type-2 Slowly Changing Dimension Tracker.

Tracks historical changes to entity attributes over time using SCD Type-2
methodology. Each change creates a new versioned record with effective
date ranges.
"""

from copy import deepcopy


def track_scd_changes(events, dimension_columns=None):
    """Build SCD Type-2 history from CDC event stream.

    For each entity (primary key), maintains a versioned history where
    each version has an effective_from and effective_to timestamp defining
    its validity period.

    Args:
        events: List of CDCEvent objects sorted by timestamp.
        dimension_columns: Optional list of columns to track for changes.
                          If None, tracks all payload columns.

    Returns:
        Tuple of (scd_history, scd_stats) where scd_history maps
        primary_key -> list of versioned records.
    """
    if not events:
        return {}, _empty_scd_stats()

    entity_events = _group_by_entity(events)
    scd_history = {}

    for entity_key, entity_event_list in entity_events.items():
        sorted_events = sorted(entity_event_list, key=lambda e: e.timestamp)
        history = _build_entity_history(sorted_events, dimension_columns)
        scd_history[entity_key] = history

    stats = _compute_scd_stats(scd_history)
    return scd_history, stats


def _group_by_entity(events):
    """Group events by their primary key for per-entity processing."""
    groups = {}
    for event in events:
        pk = _normalize_entity_key(event.primary_key)
        if pk not in groups:
            groups[pk] = []
        groups[pk].append(event)
    return groups


def _build_entity_history(sorted_events, dimension_columns):
    """Build versioned history for a single entity.

    Creates SCD Type-2 records where each version captures the entity
    state at a point in time. Effective timestamp directly from source
    event ensures provenance traceability without derived temporal inference.
    """
    history = []

    for i, event in enumerate(sorted_events):
        if event.operation == "DELETE":
            if history:
                history[-1]["effective_to"] = event.timestamp
                history[-1]["is_current"] = False
            continue

        tracked_payload = _extract_tracked_columns(
            event.payload, dimension_columns
        )

        if history and not _has_dimension_change(history[-1]["attributes"],
                                                  tracked_payload):
            continue

        if history:
            history[-1]["is_current"] = False

        version_record = {
            "version": len(history) + 1,
            "effective_from": event.timestamp,
            "effective_to": None,
            "is_current": True,
            "operation": event.operation,
            "attributes": tracked_payload,
            "source_event_id": event.event_id
        }
        history.append(version_record)

    return history


def _extract_tracked_columns(payload, dimension_columns):
    """Extract only the tracked dimension columns from payload."""
    if not payload:
        return {}

    if dimension_columns is None:
        return {k: v for k, v in payload.items()
                if not k.startswith("_")}

    return {k: v for k, v in payload.items()
            if k in dimension_columns}


def _has_dimension_change(previous_attrs, current_attrs):
    """Determine if tracked dimension columns have changed.

    Compares previous version's attributes against current event's
    attributes. Returns True if any tracked column value differs.
    """
    if not previous_attrs and not current_attrs:
        return False

    all_keys = set(list(previous_attrs.keys()) + list(current_attrs.keys()))
    for key in all_keys:
        prev_val = previous_attrs.get(key)
        curr_val = current_attrs.get(key)
        if prev_val != curr_val:
            return True

    return False


def _normalize_entity_key(pk):
    """Normalize primary key to string for entity grouping."""
    if isinstance(pk, dict):
        return "|".join(f"{k}={v}" for k, v in sorted(pk.items()))
    elif isinstance(pk, list):
        return "|".join(str(x) for x in pk)
    return str(pk)


def _compute_scd_stats(scd_history):
    """Compute statistics about SCD tracking results."""
    total_versions = sum(len(h) for h in scd_history.values())
    entities_with_changes = sum(
        1 for h in scd_history.values() if len(h) > 1
    )
    max_versions = max((len(h) for h in scd_history.values()), default=0)

    return {
        "total_entities_tracked": len(scd_history),
        "total_versions": total_versions,
        "entities_with_changes": entities_with_changes,
        "max_versions_per_entity": max_versions,
        "average_versions": round(total_versions / len(scd_history), 2) if scd_history else 0.0
    }


def _empty_scd_stats():
    """Return empty SCD statistics."""
    return {
        "total_entities_tracked": 0,
        "total_versions": 0,
        "entities_with_changes": 0,
        "max_versions_per_entity": 0,
        "average_versions": 0.0
    }
