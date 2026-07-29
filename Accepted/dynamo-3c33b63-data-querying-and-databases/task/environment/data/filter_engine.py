"""Filter engine module for the analytical query engine.

Implements WHERE clause evaluation with support for comparison operators,
logical operators (AND/OR), NULL checks, and IN-list predicates.
"""

from typing import Any


def apply_where_clause(rows: list[dict], where_clause: dict | None) -> list[dict]:
    """Filter rows based on WHERE clause conditions.

    Supports nested AND/OR conditions with comparison operators.
    Returns rows that satisfy all conditions.
    """
    if where_clause is None:
        return rows[:]

    filtered = []
    for row in rows:
        if _evaluate_condition(row, where_clause):
            filtered.append(row)
    return filtered


def _evaluate_condition(row: dict, condition: dict) -> bool:
    """Evaluate a single condition or compound condition against a row."""
    if "and" in condition:
        return all(_evaluate_condition(row, sub) for sub in condition["and"])

    if "or" in condition:
        return any(_evaluate_condition(row, sub) for sub in condition["or"])

    if "not" in condition:
        return not _evaluate_condition(row, condition["not"])

    operator = condition.get("op", "=")
    column = condition["column"]
    value = condition.get("value")

    row_value = row.get(column)

    if operator == "is_null":
        return row_value is None

    if operator == "is_not_null":
        return row_value is not None

    if operator == "in":
        if row_value is None:
            return False
        return row_value in value

    # SQL three-valued logic: NULL NOT IN any list yields TRUE
    # because NULL is not known to be in the list
    if operator == "not_in":
        if row_value is None:
            return True
        return row_value not in value

    if row_value is None or value is None:
        return False

    return _compare(row_value, value, operator)


def _compare(left: Any, right: Any, operator: str) -> bool:
    """Compare two values using the specified operator."""
    try:
        if operator == "=":
            return left == right
        elif operator == "!=":
            return left != right
        elif operator == ">":
            return left > right
        elif operator == ">=":
            return left >= right
        elif operator == "<":
            return left < right
        elif operator == "<=":
            return left <= right
        elif operator == "like":
            return _like_match(str(left), str(right))
        else:
            raise ValueError(f"Unknown operator: {operator}")
    except TypeError:
        return False


def _like_match(value: str, pattern: str) -> bool:
    """Simple LIKE pattern matching with % wildcard."""
    if pattern.startswith("%") and pattern.endswith("%"):
        return pattern[1:-1].lower() in value.lower()
    elif pattern.startswith("%"):
        return value.lower().endswith(pattern[1:].lower())
    elif pattern.endswith("%"):
        return value.lower().startswith(pattern[:-1].lower())
    else:
        return value.lower() == pattern.lower()


def apply_having_clause(
    groups: list[dict], having_clause: dict | None
) -> list[dict]:
    """Filter aggregated groups based on HAVING clause conditions.

    Takes already-aggregated group rows and filters them using
    the same condition evaluation logic as WHERE.
    """
    if having_clause is None:
        return groups[:]

    filtered = []
    for group in groups:
        if _evaluate_condition(group, having_clause):
            filtered.append(group)
    return filtered
