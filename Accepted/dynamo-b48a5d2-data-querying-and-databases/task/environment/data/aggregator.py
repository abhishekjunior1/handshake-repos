"""Aggregation engine module.

Implements GROUP BY with aggregate functions: COUNT, SUM, AVG, MIN, MAX.
Supports multiple aggregation columns per group.
"""

from typing import Any
from collections import defaultdict


def execute_aggregation(
    rows: list[dict],
    group_by: list[str],
    aggregations: list[dict],
) -> list[dict]:
    """Execute GROUP BY aggregation on input rows.

    Args:
        rows: Input rows to aggregate
        group_by: Column names to group by
        aggregations: List of aggregation specs, each with:
            - function: aggregate function name
            - column: source column (or '*' for COUNT)
            - alias: output column name

    Returns:
        Aggregated rows with group keys and computed aggregates.
    """
    groups = _build_groups(rows, group_by)
    results = []

    for group_key, group_rows in sorted(groups.items()):
        result_row = {}
        for i, col in enumerate(group_by):
            result_row[col] = group_key[i] if len(group_by) > 1 else group_key
        if len(group_by) == 1:
            result_row[group_by[0]] = group_key

        for agg in aggregations:
            alias = agg["alias"]
            value = _compute_aggregate(group_rows, agg)
            result_row[alias] = value

        results.append(result_row)

    return results


def _build_groups(rows: list[dict], group_by: list[str]) -> dict[Any, list[dict]]:
    """Group rows by the specified columns."""
    groups = defaultdict(list)
    for row in rows:
        if len(group_by) == 1:
            key = row[group_by[0]]
        else:
            key = tuple(row[col] for col in group_by)
        groups[key].append(row)
    return groups


def _compute_aggregate(rows: list[dict], agg_spec: dict) -> Any:
    """Compute a single aggregate value over a group of rows."""
    func = agg_spec["function"].upper()
    column = agg_spec["column"]

    if func == "COUNT":
        if column == "*":
            return len(rows)
        return sum(1 for row in rows if row.get(column) is not None)

    values = [row[column] for row in rows if row.get(column) is not None]

    if not values:
        return None

    if func == "SUM":
        return sum(values)
    elif func == "AVG":
        return round(sum(values) / len(values), 4)
    elif func == "MIN":
        return min(values)
    elif func == "MAX":
        return max(values)
    else:
        raise ValueError(f"Unknown aggregate function: {func}")
