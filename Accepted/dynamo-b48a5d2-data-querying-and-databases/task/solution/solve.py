"""Solution: Patches three semantic bugs in the query engine pipeline.

Bug 1 (pipeline.py): Join-then-aggregate causes fan-out inflation when the
    right table has multiple rows per join key. When all aggregation columns
    and group-by columns reference the left table, the join is unnecessary
    for aggregation. Fix: aggregate on the left table directly, using the
    join only to filter which left rows have matches.

Bug 2 (window_functions.py): Default frame mode is 'range' per SQL standard,
    but the pipeline semantics require row-by-row accumulation. Fix: change
    default to 'rows'.

Bug 3 (pipeline.py): Post-join WHERE filter removes outer rows from LEFT JOIN
    that have NULLs in the filtered column. Fix: for LEFT JOINs with a filter,
    apply the filter to the right table before joining (as ON predicate),
    stripping the right-prefix from filter column names.
"""

import os

APP_DIR = "/app"


def patch_window_functions():
    """Fix Bug 2: Change default frame_mode from 'range' to 'rows'."""
    filepath = os.path.join(APP_DIR, "window_functions.py")
    with open(filepath, "r") as f:
        content = f.read()

    content = content.replace(
        'frame_mode = spec.get("frame_mode", "range")',
        'frame_mode = spec.get("frame_mode", "rows")',
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_pipeline():
    """Fix Bug 1 and Bug 3 in the join-aggregate execution."""
    filepath = os.path.join(APP_DIR, "pipeline.py")
    with open(filepath, "r") as f:
        content = f.read()

    old_function = '''def _execute_join_aggregate_query(query, tables):
    """Execute a join followed by aggregation.

    Steps:
        1. Resolve left and right tables
        2. Perform the join operation
        3. Apply any post-join filters
        4. Execute aggregation with GROUP BY
    """
    join_spec = query["join"]
    left_table = tables[join_spec["left_table"]]
    right_table = tables[join_spec["right_table"]]

    joined = execute_join(left_table, right_table, join_spec)

    post_filter = query.get("filter")
    if post_filter:
        joined = apply_where_clause(joined, post_filter)

    group_by = query["group_by"]
    aggregations = query["aggregations"]

    return execute_aggregation(joined, group_by, aggregations)'''

    new_function = '''def _execute_join_aggregate_query(query, tables):
    """Execute a join followed by aggregation.

    Steps:
        1. Resolve left and right tables
        2. For LEFT JOINs with filters, apply filter to right table before join
        3. Perform the join operation
        4. Handle fan-out: aggregate on source when possible
        5. Execute aggregation with GROUP BY
    """
    join_spec = query["join"]
    left_table = tables[join_spec["left_table"]]
    right_table = tables[join_spec["right_table"]]
    left_prefix = join_spec.get("left_prefix", "l_")
    right_prefix = join_spec.get("right_prefix", "r_")

    post_filter = query.get("filter")

    # Bug 3 fix: For LEFT JOINs, apply filter as ON predicate (before join)
    # to preserve outer rows that would otherwise be eliminated by WHERE on NULLs
    if post_filter and join_spec["type"].lower() == "left":
        # Strip right prefix from filter columns for pre-join application
        adapted = _strip_prefix_from_filter(post_filter, right_prefix)
        right_table = apply_where_clause(right_table, adapted)
        post_filter = None

    group_by = query["group_by"]
    aggregations = query["aggregations"]

    # Bug 1 fix: Check if all aggregation and group-by columns are from the
    # left table. If so, aggregate on left table directly to avoid fan-out.
    agg_columns = [a["column"] for a in aggregations]
    all_left = all(
        col == "*" or col.startswith(left_prefix) for col in agg_columns
    )
    all_group_left = all(g.startswith(left_prefix) for g in group_by)

    if all_left and all_group_left:
        # Use join only to identify matching left rows, then aggregate on source
        joined = execute_join(left_table, right_table, join_spec)
        if post_filter:
            joined = apply_where_clause(joined, post_filter)

        # Extract distinct left keys from join result
        left_on = join_spec["left_on"]
        left_key_col = f"{left_prefix}{left_on}"
        matched_keys = set(row[left_key_col] for row in joined)

        # Build source rows with prefixed names, deduped
        source_rows = []
        for row in left_table:
            if row[left_on] in matched_keys:
                prefixed = {f"{left_prefix}{k}": v for k, v in row.items()}
                source_rows.append(prefixed)

        return execute_aggregation(source_rows, group_by, aggregations)
    else:
        joined = execute_join(left_table, right_table, join_spec)
        if post_filter:
            joined = apply_where_clause(joined, post_filter)
        return execute_aggregation(joined, group_by, aggregations)


def _strip_prefix_from_filter(filter_spec, prefix):
    """Remove column prefix from filter for pre-join application."""
    if isinstance(filter_spec, list):
        return [_strip_prefix_from_filter(f, prefix) for f in filter_spec]
    adapted = dict(filter_spec)
    col = adapted.get("column", "")
    if col.startswith(prefix):
        adapted["column"] = col[len(prefix):]
    return adapted'''

    content = content.replace(old_function, new_function)

    with open(filepath, "w") as f:
        f.write(content)


def main():
    patch_window_functions()
    patch_pipeline()
    print("All patches applied successfully.")


if __name__ == "__main__":
    main()
