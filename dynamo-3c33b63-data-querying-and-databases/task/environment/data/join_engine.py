"""Join engine module for the analytical query engine.

Implements multi-table JOIN operations: INNER JOIN, LEFT JOIN,
RIGHT JOIN, and CROSS JOIN with composite key support.
"""

from typing import Any


def execute_join(
    left_rows: list[dict],
    right_rows: list[dict],
    join_spec: dict,
) -> list[dict]:
    """Execute a JOIN operation between two tables.

    join_spec contains:
      - type: "inner", "left", "right", "cross"
      - on: list of {"left": col, "right": col} key pairs
      - filter: optional additional filter condition on right-side columns
    """
    join_type = join_spec.get("type", "inner").lower()
    join_keys = join_spec.get("on", [])

    if join_type == "cross":
        return _cross_join(left_rows, right_rows)
    elif join_type == "inner":
        return _inner_join(left_rows, right_rows, join_keys)
    elif join_type == "left":
        return _left_join(left_rows, right_rows, join_keys)
    elif join_type == "right":
        return _right_join(left_rows, right_rows, join_keys)
    else:
        raise ValueError(f"Unknown join type: {join_type}")


def _build_join_index(
    rows: list[dict], key_columns: list[str]
) -> dict[tuple, list[dict]]:
    """Build a hash index for join lookups."""
    index = {}
    for row in rows:
        key = tuple(row.get(col) for col in key_columns)
        if key not in index:
            index[key] = []
        index[key].append(row)
    return index


def _merge_rows(
    left_row: dict,
    right_row: dict | None,
    right_columns: set[str],
) -> dict:
    """Merge two rows into a single result row.

    Left table columns are prefixed with 'l_' and right table columns
    with 'r_' to avoid naming conflicts.
    """
    merged = {}

    for col, val in left_row.items():
        merged[f"l_{col}"] = val

    if right_row:
        for col, val in right_row.items():
            merged[f"r_{col}"] = val
    else:
        for col in right_columns:
            merged[f"r_{col}"] = None

    return merged


def _get_right_columns(right_rows: list[dict]) -> set[str]:
    """Get column names from right table."""
    if right_rows:
        return set(right_rows[0].keys())
    return set()


def _inner_join(
    left_rows: list[dict],
    right_rows: list[dict],
    join_keys: list[dict],
) -> list[dict]:
    """Execute INNER JOIN - only matching rows from both sides."""
    right_key_cols = [k["right"] for k in join_keys]
    left_key_cols = [k["left"] for k in join_keys]
    right_index = _build_join_index(right_rows, right_key_cols)
    right_columns = _get_right_columns(right_rows)

    results = []
    for left_row in left_rows:
        left_key = tuple(left_row.get(col) for col in left_key_cols)
        matching_rights = right_index.get(left_key, [])
        for right_row in matching_rights:
            merged = _merge_rows(left_row, right_row, right_columns)
            results.append(merged)

    return results


def _left_join(
    left_rows: list[dict],
    right_rows: list[dict],
    join_keys: list[dict],
) -> list[dict]:
    """Execute LEFT JOIN - all left rows, matching right rows or NULL."""
    right_key_cols = [k["right"] for k in join_keys]
    left_key_cols = [k["left"] for k in join_keys]
    right_index = _build_join_index(right_rows, right_key_cols)
    right_columns = _get_right_columns(right_rows)

    results = []
    for left_row in left_rows:
        left_key = tuple(left_row.get(col) for col in left_key_cols)
        matching_rights = right_index.get(left_key, [])
        if matching_rights:
            for right_row in matching_rights:
                merged = _merge_rows(left_row, right_row, right_columns)
                results.append(merged)
        else:
            merged = _merge_rows(left_row, None, right_columns)
            results.append(merged)

    return results


def _right_join(
    left_rows: list[dict],
    right_rows: list[dict],
    join_keys: list[dict],
) -> list[dict]:
    """Execute RIGHT JOIN - all right rows, matching left rows or NULL."""
    reversed_keys = [{"left": k["right"], "right": k["left"]} for k in join_keys]
    result = _left_join(right_rows, left_rows, reversed_keys)
    # Swap prefixes back
    swapped = []
    for row in result:
        new_row = {}
        for k, v in row.items():
            if k.startswith("l_"):
                new_row[f"r_{k[2:]}"] = v
            elif k.startswith("r_"):
                new_row[f"l_{k[2:]}"] = v
            else:
                new_row[k] = v
        swapped.append(new_row)
    return swapped


def _cross_join(left_rows: list[dict], right_rows: list[dict]) -> list[dict]:
    """Execute CROSS JOIN - cartesian product of both tables."""
    results = []
    right_columns = _get_right_columns(right_rows)
    for left_row in left_rows:
        for right_row in right_rows:
            merged = _merge_rows(left_row, right_row, right_columns)
            results.append(merged)
    return results
