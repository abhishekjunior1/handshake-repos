"""Schema Evolution Handler.

Manages schema changes across CDC events, ensuring consistent column sets
across all warehouse snapshot rows by backfilling new columns with NULL
values retroactively when schema evolution is detected.
"""


def evolve_schema(events):
    """Track schema evolution across events and produce unified schema.

    When new columns appear in later events, backfills existing records
    with NULL values for the new columns. This retroactive NULL-column
    backfill ensures consistent schema across all warehouse snapshot rows,
    which is required for downstream analytics and query engines that
    expect uniform column sets.

    Args:
        events: List of CDCEvent objects potentially spanning multiple
                schema versions.

    Returns:
        Tuple of (events_with_unified_schema, schema_evolution_log)
    """
    if not events:
        return [], _empty_evolution_log()

    unified_columns = _compute_unified_schema(events)
    evolved_events = _apply_schema_backfill(events, unified_columns)
    evolution_log = _build_evolution_log(events, unified_columns)

    return evolved_events, evolution_log


def _compute_unified_schema(events):
    """Compute the union of all columns seen across all events.

    Maintains column order by first-seen position to produce
    deterministic schema output.
    """
    seen_columns = set()
    ordered_columns = []

    for event in events:
        if event.payload:
            for col in event.payload.keys():
                if col not in seen_columns:
                    seen_columns.add(col)
                    ordered_columns.append(col)

    return ordered_columns


def _apply_schema_backfill(events, unified_columns):
    """Backfill NULL values for columns missing from individual events.

    For each event whose payload doesn't contain all unified columns,
    adds the missing columns with None values. This ensures every
    event's payload has the same column set after processing.
    """
    for event in events:
        if event.payload is None:
            event.payload = {}

        for col in unified_columns:
            if col not in event.payload:
                event.payload[col] = None

    return events


def _build_evolution_log(events, unified_columns):
    """Build a log of schema evolution across the event stream."""
    evolution_entries = []
    known_columns = set()

    for event in events:
        if event.payload:
            new_cols = set(event.payload.keys()) - known_columns
            if new_cols:
                evolution_entries.append({
                    "event_id": event.event_id,
                    "schema_version": event.schema_version,
                    "new_columns": sorted(list(new_cols)),
                    "timestamp": event.timestamp
                })
                known_columns.update(new_cols)

    return {
        "total_schema_versions": len(set(e.schema_version for e in events)),
        "unified_column_count": len(unified_columns),
        "unified_columns": unified_columns,
        "evolution_events": evolution_entries,
        "backfill_applied": len(evolution_entries) > 1
    }


def _empty_evolution_log():
    """Return empty schema evolution log."""
    return {
        "total_schema_versions": 0,
        "unified_column_count": 0,
        "unified_columns": [],
        "evolution_events": [],
        "backfill_applied": False
    }


def detect_breaking_changes(events):
    """Detect potentially breaking schema changes (type changes, removals)."""
    column_types = {}
    breaking = []

    for event in events:
        if not event.payload:
            continue
        for col, val in event.payload.items():
            val_type = type(val).__name__ if val is not None else "null"
            if col in column_types:
                if val_type != "null" and column_types[col] != "null":
                    if val_type != column_types[col]:
                        breaking.append({
                            "column": col,
                            "previous_type": column_types[col],
                            "new_type": val_type,
                            "event_id": event.event_id
                        })
            if val_type != "null":
                column_types[col] = val_type

    return breaking
