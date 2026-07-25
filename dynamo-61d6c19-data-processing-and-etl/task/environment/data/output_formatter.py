"""CDC Pipeline Output Formatter.

Formats the final warehouse snapshot and pipeline metrics into the
output JSON structure.
"""

import json


def format_output(merged_state, dedup_stats, schema_log,
                  merge_stats, scd_history, scd_stats):
    """Format all pipeline outputs into final JSON structure.

    Args:
        merged_state: Dict of primary_key -> current row state.
        dedup_stats: Deduplication metrics dict.
        schema_log: Schema evolution log dict.
        merge_stats: Merge operation statistics dict.
        scd_history: SCD Type-2 history dict.
        scd_stats: SCD tracking statistics dict.

    Returns:
        Dict containing the complete pipeline output.
    """
    snapshot_rows = _format_snapshot_rows(merged_state)
    scd_records = _format_scd_history(scd_history)

    output = {
        "warehouse_snapshot": {
            "rows": snapshot_rows,
            "row_count": len(snapshot_rows),
            "active_count": sum(1 for r in snapshot_rows if not r.get("_deleted", False)),
            "deleted_count": sum(1 for r in snapshot_rows if r.get("_deleted", False))
        },
        "scd_history": {
            "records": scd_records,
            "total_versions": scd_stats.get("total_versions", 0),
            "entities_tracked": scd_stats.get("total_entities_tracked", 0),
            "entities_with_changes": scd_stats.get("entities_with_changes", 0)
        },
        "pipeline_metrics": {
            "deduplication": dedup_stats,
            "schema_evolution": {
                "versions_detected": schema_log.get("total_schema_versions", 0),
                "unified_columns": schema_log.get("unified_columns", []),
                "backfill_applied": schema_log.get("backfill_applied", False)
            },
            "merge_operations": merge_stats
        }
    }

    return output


def _format_snapshot_rows(merged_state):
    """Format merged state into ordered list of snapshot rows."""
    rows = []
    for pk in sorted(merged_state.keys()):
        row = dict(merged_state[pk])
        rows.append(row)
    return rows


def _format_scd_history(scd_history):
    """Format SCD history into flat list of versioned records."""
    records = []
    for entity_key in sorted(scd_history.keys()):
        versions = scd_history[entity_key]
        for version in versions:
            record = dict(version)
            record["entity_key"] = entity_key
            records.append(record)
    return records


def write_output(output, filepath):
    """Write formatted output to JSON file."""
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2, default=str)
