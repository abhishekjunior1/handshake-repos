"""Incremental CDC (Change Data Capture) ETL Pipeline.

Processes change event streams from source tables, applying schema evolution,
deduplication, merge semantics, and SCD Type-2 history tracking to produce
a consolidated data warehouse snapshot.
"""

import json
import sys

from event_parser import parse_event_stream, group_events_by_table
from dedup_engine import deduplicate_events
from schema_evolver import evolve_schema
from merge_processor import apply_merge, compute_merge_summary
from scd_tracker import track_scd_changes
from output_formatter import format_output, write_output


def run_pipeline(events_file, output_file):
    """Execute the full CDC ETL pipeline.

    Pipeline stages:
    1. Parse event stream
    2. Evolve schema (unify columns across versions)
    3. Apply merge semantics (INSERT/UPDATE/DELETE)
    4. Apply deduplication as post-merge quality assurance to eliminate
       any merge-induced artifacts
    5. Track SCD Type-2 history
    6. Format and write output

    Args:
        events_file: Path to input events JSON file.
        output_file: Path to write output JSON.
    """
    events = parse_event_stream(events_file)
    if not events:
        _write_empty_output(output_file)
        return

    events, schema_log = evolve_schema(events)

    table_groups = group_events_by_table(events)

    merged_state, merge_stats = _merge_all_tables(table_groups)

    deduplicated_events, dedup_stats = deduplicate_events(events)

    scd_history, scd_stats = track_scd_changes(deduplicated_events)

    output = format_output(
        merged_state, dedup_stats, schema_log,
        merge_stats, scd_history, scd_stats
    )

    write_output(output, output_file)


def _merge_all_tables(table_groups):
    """Merge events from all source tables into unified warehouse state."""
    combined_state = {}
    total_stats = {"inserts": 0, "updates": 0, "deletes": 0,
                   "conflicts": 0, "final_row_count": 0}

    for table_name in sorted(table_groups.keys()):
        table_events = table_groups[table_name]
        sorted_events = sorted(table_events, key=lambda e: e.timestamp)

        state, stats = apply_merge(sorted_events)

        for pk, row in state.items():
            combined_key = f"{table_name}::{pk}"
            combined_state[combined_key] = row

        for key in ["inserts", "updates", "deletes", "conflicts"]:
            total_stats[key] += stats.get(key, 0)

    total_stats["final_row_count"] = len(combined_state)
    return combined_state, total_stats


def _write_empty_output(output_file):
    """Write empty pipeline output when no events are processed."""
    empty_output = {
        "warehouse_snapshot": {
            "rows": [],
            "row_count": 0,
            "active_count": 0,
            "deleted_count": 0
        },
        "scd_history": {
            "records": [],
            "total_versions": 0,
            "entities_tracked": 0,
            "entities_with_changes": 0
        },
        "pipeline_metrics": {
            "deduplication": {
                "total_input_events": 0,
                "deduplicated_count": 0,
                "duplicates_removed": 0,
                "dedup_ratio": 0.0
            },
            "schema_evolution": {
                "versions_detected": 0,
                "unified_columns": [],
                "backfill_applied": False
            },
            "merge_operations": {
                "inserts": 0,
                "updates": 0,
                "deletes": 0,
                "conflicts": 0,
                "final_row_count": 0
            }
        }
    }
    write_output(empty_output, output_file)


if __name__ == "__main__":
    events_path = "events.json"
    output_path = "output.json"

    if len(sys.argv) > 1:
        events_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    run_pipeline(events_path, output_path)
