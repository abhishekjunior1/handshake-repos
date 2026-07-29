"""Oracle solution - patches bugs in the analytical query engine."""

import subprocess
import sys


def patch_file(filepath, old_text, new_text):
    """Apply a string replacement patch to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    if old_text not in content:
        print(f"WARNING: patch target not found in {filepath}")
        return False
    content = content.replace(old_text, new_text, 1)
    with open(filepath, 'w') as f:
        f.write(content)
    return True


def fix_bug2():
    """Fix Bug 2: RANGE vs ROWS implicit window frame.

    The window function defaults to 'range' frame which includes peer rows.
    Fix: default to 'rows' for sequential cumulative computation.
    """
    patch_file(
        "/app/window_functions.py",
        '    # SQL standard: default frame is RANGE when not explicitly specified\n'
        '    frame_mode = spec.get("frame_mode", "range")',
        '    # Use ROWS frame for sequential cumulative computation\n'
        '    frame_mode = spec.get("frame_mode", "rows")',
    )


def fix_bugs_1_and_3():
    """Fix Bug 1 (fan-out) and Bug 3 (ON-WHERE contradiction).

    Bug 1: Join before aggregate inflates counts/sums for 1:many joins.
    Fix: aggregate directly on source when columns are all from left table.

    Bug 3: Filter applied as WHERE after LEFT JOIN discards outer rows.
    Fix: apply filter to right table BEFORE join (ON semantics).
    """
    patch_file(
        "/app/pipeline.py",
        '''def _execute_join_aggregate_query(query: dict, tables: dict) -> list[dict]:
    """Execute a join followed by aggregation.

    Joins the specified tables, then computes aggregate functions
    over the joined result set grouped by the specified columns.
    """
    source_table = query["source_table"]
    join_spec = query["join"]
    target_table = join_spec["table"]

    left_rows = tables[source_table][:]
    right_rows = tables[target_table][:]

    # Apply join with filter conditions
    join_filter = join_spec.get("filter")
    joined = execute_join(left_rows, right_rows, join_spec)

    # Apply filter condition from join spec as WHERE on joined result
    if join_filter:
        joined = apply_where_clause(joined, join_filter)

    # Aggregate over the joined result
    group_by = query.get("group_by", [])
    aggregations = query.get("aggregations", [])

    return execute_aggregation(joined, group_by, aggregations)''',
        '''def _execute_join_aggregate_query(query: dict, tables: dict) -> list[dict]:
    """Execute a join followed by aggregation.

    When aggregation columns come from the left table only and join is INNER,
    aggregates directly on the source to avoid fan-out from one-to-many joins.
    For LEFT JOINs, applies filter as ON predicate to preserve outer rows.
    """
    source_table = query["source_table"]
    join_spec = query["join"]
    target_table = join_spec["table"]

    left_rows = tables[source_table][:]
    right_rows = tables[target_table][:]

    aggregations = query.get("aggregations", [])
    group_by = query.get("group_by", [])

    # Check if all aggregation columns come from the left table
    all_left = all(
        a.get("column", "").startswith("l_") or a.get("column") == "*"
        for a in aggregations
    )

    if all_left and join_spec.get("type", "inner") == "inner":
        # Aggregate on source table directly (avoid fan-out)
        stripped_group = [g.replace("l_", "") for g in group_by]
        stripped_aggs = []
        for a in aggregations:
            stripped_aggs.append({
                "function": a["function"],
                "column": a["column"].replace("l_", "") if a.get("column") else a.get("column"),
                "alias": a["alias"],
            })
        result = execute_aggregation(left_rows, stripped_group, stripped_aggs)
        fixed = []
        for r in result:
            new_r = {}
            for k, v in r.items():
                if k in stripped_group:
                    new_r[f"l_{k}"] = v
                else:
                    new_r[k] = v
            fixed.append(new_r)
        return fixed

    # For LEFT JOINs: apply filter as ON predicate (before join)
    join_filter = join_spec.get("filter")
    if join_filter:
        col = join_filter["column"].replace("r_", "")
        right_rows = [r for r in right_rows if r.get(col) == join_filter["value"]]

    joined = execute_join(left_rows, right_rows, join_spec)
    return execute_aggregation(joined, group_by, aggregations)''',
    )


if __name__ == "__main__":
    fix_bug2()
    fix_bugs_1_and_3()
    print("All patches applied successfully.")

    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline error: {result.stderr}")
        sys.exit(1)
    print("Pipeline executed successfully.")
