"""Filter engine module.

Evaluates WHERE clause conditions against row data.
Supports comparison operators and AND logic for combining conditions.
"""

from typing import Any


def apply_where_clause(rows: list[dict], filter_spec: dict | list) -> list[dict]:
    """Apply filter conditions to a list of rows.

    Args:
        rows: Input rows to filter
        filter_spec: Single condition dict or list of conditions (AND logic)

    Returns:
        Filtered rows matching all conditions.
    """
    if isinstance(filter_spec, dict):
        conditions = [filter_spec]
    else:
        conditions = filter_spec

    return [row for row in rows if _evaluate_conditions(row, conditions)]


def _evaluate_conditions(row: dict, conditions: list[dict]) -> bool:
    """Evaluate all conditions against a row (AND logic)."""
    return all(_evaluate_single(row, cond) for cond in conditions)


def _evaluate_single(row: dict, condition: dict) -> bool:
    """Evaluate a single condition against a row.

    Condition format:
        {"column": str, "op": str, "value": any}

    Supported operators: =, !=, <, <=, >, >=, in, not_in, is_null, is_not_null
    """
    column = condition["column"]
    op = condition["op"]
    expected = condition.get("value")

    actual = row.get(column)

    if op == "is_null":
        return actual is None
    if op == "is_not_null":
        return actual is not None

    if actual is None:
        return False

    return _compare(actual, op, expected)


def _compare(actual: Any, op: str, expected: Any) -> bool:
    """Perform comparison operation."""
    if op == "=":
        return actual == expected
    elif op == "!=":
        return actual != expected
    elif op == "<":
        return actual < expected
    elif op == "<=":
        return actual <= expected
    elif op == ">":
        return actual > expected
    elif op == ">=":
        return actual >= expected
    elif op == "in":
        return actual in expected
    elif op == "not_in":
        return actual not in expected
    else:
        raise ValueError(f"Unsupported operator: {op}")
