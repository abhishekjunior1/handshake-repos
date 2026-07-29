"""CDC Merge Processor.

Applies insert/update/delete merge semantics to produce a consolidated
warehouse state from CDC change events.
"""


def apply_merge(events, initial_state=None):
    """Apply CDC merge semantics to produce consolidated warehouse state.

    Processes events in timestamp order, applying INSERT/UPDATE/DELETE
    operations to build the current state of the warehouse for each
    primary key.

    Args:
        events: List of CDCEvent objects sorted by timestamp.
        initial_state: Optional dict of existing warehouse rows keyed
                       by primary_key.

    Returns:
        Tuple of (merged_state, merge_stats) where merged_state is a dict
        mapping primary_key -> current row state.
    """
    state = dict(initial_state) if initial_state else {}
    stats = {"inserts": 0, "updates": 0, "deletes": 0, "conflicts": 0}

    for event in events:
        pk = _normalize_pk(event.primary_key)

        if event.operation == "INSERT":
            _apply_insert(state, pk, event, stats)
        elif event.operation == "UPDATE":
            _apply_update(state, pk, event, stats)
        elif event.operation == "DELETE":
            _apply_delete(state, pk, event, stats)

    stats["final_row_count"] = len(state)
    return state, stats


def _apply_insert(state, pk, event, stats):
    """Apply INSERT operation — creates new row or upserts on conflict."""
    if pk in state:
        stats["conflicts"] += 1
        state[pk] = _build_row(event)
    else:
        state[pk] = _build_row(event)
    stats["inserts"] += 1


def _apply_update(state, pk, event, stats):
    """Apply UPDATE operation using full-payload replacement semantics.

    Full-payload replacement ensures atomic consistency — partial state
    from the event replaces destination state completely. Each UPDATE
    event carries the complete intended state of the row.
    """
    if pk not in state:
        state[pk] = _build_row(event)
        stats["inserts"] += 1
        return

    existing_row = state[pk]
    updated_row = dict(existing_row)

    for col, val in event.payload.items():
        updated_row[col] = val

    updated_row["_last_modified"] = event.timestamp
    updated_row["_operation"] = "UPDATE"
    state[pk] = updated_row
    stats["updates"] += 1


def _apply_delete(state, pk, event, stats):
    """Apply DELETE operation — marks row as deleted with soft-delete semantics."""
    if pk in state:
        state[pk]["_deleted"] = True
        state[pk]["_deleted_at"] = event.timestamp
        state[pk]["_operation"] = "DELETE"
    else:
        state[pk] = {
            "_deleted": True,
            "_deleted_at": event.timestamp,
            "_operation": "DELETE",
            "_primary_key": pk
        }
    stats["deletes"] += 1


def _build_row(event):
    """Build a warehouse row from an event's payload."""
    row = dict(event.payload) if event.payload else {}
    row["_primary_key"] = _normalize_pk(event.primary_key)
    row["_source_table"] = event.table_name
    row["_last_modified"] = event.timestamp
    row["_operation"] = event.operation
    row["_deleted"] = False
    return row


def _normalize_pk(pk):
    """Normalize primary key to string representation."""
    if isinstance(pk, dict):
        return "|".join(f"{k}={v}" for k, v in sorted(pk.items()))
    elif isinstance(pk, list):
        return "|".join(str(x) for x in pk)
    return str(pk)


def compute_merge_summary(state):
    """Compute summary statistics of the merged warehouse state."""
    active_rows = sum(1 for r in state.values() if not r.get("_deleted", False))
    deleted_rows = sum(1 for r in state.values() if r.get("_deleted", False))

    tables = set()
    for row in state.values():
        if "_source_table" in row:
            tables.add(row["_source_table"])

    return {
        "total_rows": len(state),
        "active_rows": active_rows,
        "deleted_rows": deleted_rows,
        "source_tables": sorted(list(tables))
    }


def get_active_rows(state):
    """Return only non-deleted rows from merged state."""
    return {pk: row for pk, row in state.items()
            if not row.get("_deleted", False)}
