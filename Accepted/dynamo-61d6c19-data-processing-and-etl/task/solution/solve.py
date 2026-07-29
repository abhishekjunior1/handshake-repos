"""Solution for CDC ETL Pipeline.

Fixes three bugs:
1. pipeline.py: Moves deduplication before merge (correct ordering)
2. merge_processor.py: Changes UPDATE to partial semantics (only non-NULL overwrites)
3. scd_tracker.py: Closes previous version's effective_to when new version starts
"""

import subprocess
import sys


def apply_patches():
    """Apply all three bug fixes."""

    # Fix 1: pipeline.py - dedup BEFORE merge (not after)
    fix_pipeline()

    # Fix 2: merge_processor.py - partial update (skip NULLs)
    fix_merge_processor()

    # Fix 3: scd_tracker.py - close previous version effective_to
    fix_scd_tracker()


def fix_pipeline():
    """Fix pipeline.py: move deduplication before merge."""
    with open("/app/pipeline.py", "r") as f:
        content = f.read()

    # The buggy pipeline does:
    #   merge_all_tables(table_groups)
    #   deduplicate_events(events)
    #   track_scd_changes(deduplicated_events)
    #
    # Fix: dedup first, then group and merge the deduplicated events

    old = """    events, schema_log = evolve_schema(events)

    table_groups = group_events_by_table(events)

    merged_state, merge_stats = _merge_all_tables(table_groups)

    deduplicated_events, dedup_stats = deduplicate_events(events)

    scd_history, scd_stats = track_scd_changes(deduplicated_events)"""

    new = """    events, schema_log = evolve_schema(events)

    deduplicated_events, dedup_stats = deduplicate_events(events)

    table_groups = group_events_by_table(deduplicated_events)

    merged_state, merge_stats = _merge_all_tables(table_groups)

    scd_history, scd_stats = track_scd_changes(deduplicated_events)"""

    if old not in content:
        print("WARNING: pipeline.py patch target not found", file=sys.stderr)
        return

    content = content.replace(old, new)

    with open("/app/pipeline.py", "w") as f:
        f.write(content)


def fix_merge_processor():
    """Fix merge_processor.py: use partial update semantics for UPDATE events."""
    with open("/app/merge_processor.py", "r") as f:
        content = f.read()

    old = """    existing_row = state[pk]
    updated_row = dict(existing_row)

    for col, val in event.payload.items():
        updated_row[col] = val"""

    new = """    existing_row = state[pk]
    updated_row = dict(existing_row)

    for col, val in event.payload.items():
        if val is not None:
            updated_row[col] = val"""

    if old not in content:
        print("WARNING: merge_processor.py patch target not found", file=sys.stderr)
        return

    content = content.replace(old, new)

    with open("/app/merge_processor.py", "w") as f:
        f.write(content)


def fix_scd_tracker():
    """Fix scd_tracker.py: close previous version when new version starts."""
    with open("/app/scd_tracker.py", "r") as f:
        content = f.read()

    old = """        if history:
            history[-1]["is_current"] = False

        version_record = {"""

    new = """        if history:
            history[-1]["effective_to"] = event.timestamp
            history[-1]["is_current"] = False

        version_record = {"""

    if old not in content:
        print("WARNING: scd_tracker.py patch target not found", file=sys.stderr)
        return

    content = content.replace(old, new)

    with open("/app/scd_tracker.py", "w") as f:
        f.write(content)


if __name__ == "__main__":
    apply_patches()
    subprocess.run([sys.executable, "/app/pipeline.py"], check=True)
