"""Aggregator module for the analytical query engine.

Implements GROUP BY with aggregation functions (COUNT, SUM, AVG, MIN, MAX),
and post-aggregation HAVING clause filtering.
"""

from typing import Any

from filter_engine import apply_having_clause


def execute_aggregation(
    rows: list[dict],
    group_by: list[str],
    aggregations: list[dict],
    having_clause: dict | None = None,
) -> list[dict]:
    """Execute GROUP BY aggregation with optional HAVING filter.

    Groups rows by the specified columns, computes aggregate functions
    for each group, then applies HAVING clause to filter groups.
    """
    groups = _build_groups(rows, group_by)
    aggregated = _compute_aggregates(groups, group_by, aggregations)

    if having_clause is not None:
        aggregated = apply_having_clause(aggregated, having_clause)

    return aggregated


def _build_groups(rows: list[dict], group_by: list[str]) -> dict[tuple, list[dict]]:
    """Partition rows into groups based on GROUP BY columns."""
    groups = {}
    for row in rows:
        key = tuple(row.get(col) for col in group_by)
        if key not in groups:
            groups[key] = []
        groups[key].append(row)
    return groups


def _compute_aggregates(
    groups: dict[tuple, list[dict]],
    group_by: list[str],
    aggregations: list[dict],
) -> list[dict]:
    """Compute aggregate values for each group."""
    results = []
    for key, group_rows in groups.items():
        row = {}
        for i, col in enumerate(group_by):
            row[col] = key[i]

        for agg in aggregations:
            alias = agg.get("alias", f"{agg['function']}_{agg.get('column', '')}")
            value = _compute_single_aggregate(group_rows, agg)
            row[alias] = value

        results.append(row)
    return results


def _compute_single_aggregate(rows: list[dict], agg: dict) -> Any:
    """Compute a single aggregate function over a group of rows."""
    func = agg["function"].upper()
    column = agg.get("column")

    if func == "COUNT":
        if column == "*" or column is None:
            return len(rows)
        return sum(1 for r in rows if r.get(column) is not None)

    if column is None:
        return None

    values = [r[column] for r in rows if r.get(column) is not None]
    if not values:
        return None

    if func == "SUM":
        return sum(values)
    elif func == "AVG":
        return round(sum(values) / len(values), 2)
    elif func == "MIN":
        return min(values)
    elif func == "MAX":
        return max(values)
    elif func == "COUNT_DISTINCT":
        return len(set(values))
    else:
        raise ValueError(f"Unknown aggregate function: {func}")
