"""Join engine module.

Implements INNER JOIN and LEFT JOIN operations between two tables.
Handles column prefixing to avoid name collisions.
"""

from typing import Any


def execute_join(
    left_rows: list[dict],
    right_rows: list[dict],
    join_spec: dict,
) -> list[dict]:
    """Execute a join between two tables.

    Args:
        left_rows: Left table rows
        right_rows: Right table rows
        join_spec: Join specification with:
            - type: 'inner' or 'left'
            - left_on: join key column in left table
            - right_on: join key column in right table
            - left_prefix: prefix for left columns (optional)
            - right_prefix: prefix for right columns (optional)

    Returns:
        Joined rows with prefixed column names.
    """
    join_type = join_spec["type"].lower()
    left_on = join_spec["left_on"]
    right_on = join_spec["right_on"]
    left_prefix = join_spec.get("left_prefix", "l_")
    right_prefix = join_spec.get("right_prefix", "r_")

    right_index = _build_index(right_rows, right_on)

    if join_type == "inner":
        return _inner_join(left_rows, right_index, left_on, left_prefix, right_prefix, right_rows)
    elif join_type == "left":
        return _left_join(left_rows, right_index, left_on, left_prefix, right_prefix, right_rows)
    else:
        raise ValueError(f"Unsupported join type: {join_type}")


def _build_index(rows: list[dict], key_column: str) -> dict[Any, list[dict]]:
    """Build a hash index on a column for efficient lookups."""
    index: dict[Any, list[dict]] = {}
    for row in rows:
        key = row[key_column]
        if key not in index:
            index[key] = []
        index[key].append(row)
    return index


def _inner_join(
    left_rows: list[dict],
    right_index: dict[Any, list[dict]],
    left_on: str,
    left_prefix: str,
    right_prefix: str,
    right_rows: list[dict],
) -> list[dict]:
    """Perform inner join using hash lookup."""
    results = []
    right_columns = _get_columns(right_rows)

    for left_row in left_rows:
        key = left_row[left_on]
        matching = right_index.get(key, [])
        for right_row in matching:
            combined = _combine_rows(left_row, right_row, left_prefix, right_prefix)
            results.append(combined)

    return results


def _left_join(
    left_rows: list[dict],
    right_index: dict[Any, list[dict]],
    left_on: str,
    left_prefix: str,
    right_prefix: str,
    right_rows: list[dict],
) -> list[dict]:
    """Perform left join, preserving all left rows."""
    results = []
    right_columns = _get_columns(right_rows)

    for left_row in left_rows:
        key = left_row[left_on]
        matching = right_index.get(key, [])

        if matching:
            for right_row in matching:
                combined = _combine_rows(left_row, right_row, left_prefix, right_prefix)
                results.append(combined)
        else:
            combined = _combine_with_nulls(left_row, right_columns, left_prefix, right_prefix)
            results.append(combined)

    return results


def _combine_rows(left_row: dict, right_row: dict, left_prefix: str, right_prefix: str) -> dict:
    """Combine two rows with column prefixes."""
    combined = {}
    for col, val in left_row.items():
        combined[f"{left_prefix}{col}"] = val
    for col, val in right_row.items():
        combined[f"{right_prefix}{col}"] = val
    return combined


def _combine_with_nulls(
    left_row: dict,
    right_columns: list[str],
    left_prefix: str,
    right_prefix: str,
) -> dict:
    """Combine left row with NULL values for all right columns."""
    combined = {}
    for col, val in left_row.items():
        combined[f"{left_prefix}{col}"] = val
    for col in right_columns:
        combined[f"{right_prefix}{col}"] = None
    return combined


def _get_columns(rows: list[dict]) -> list[str]:
    """Extract column names from first row of table."""
    if not rows:
        return []
    return list(rows[0].keys())
