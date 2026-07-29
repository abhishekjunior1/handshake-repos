"""
Query execution primitives for the MVCC query engine.

Provides predicate evaluation and column projection on visible row sets.
These operate on already-filtered (visibility-checked) rows.
"""


def execute_select(rows, query):
    """Execute a SELECT query on visible rows.

    Args:
        rows: List of visible row dicts
        query: Query specification with predicates and select list

    Returns:
        List of result row dicts
    """
    filtered = apply_predicates(rows, query.get('predicates', []))
    projected = project_columns(filtered, query['select'])
    return projected


def apply_predicates(rows, predicates):
    """Apply WHERE predicates to filter rows.

    Supports: =, !=, <, >, <=, >=, IS NULL, IS NOT NULL, IN, BETWEEN

    Args:
        rows: List of row dicts
        predicates: List of predicate specs

    Returns:
        Filtered list of rows
    """
    if not predicates:
        return list(rows)

    result = []
    for row in rows:
        if all(_evaluate_predicate(row, pred) for pred in predicates):
            result.append(row)
    return result


def _evaluate_predicate(row, predicate):
    """Evaluate a single predicate against a row.

    Args:
        row: Row dictionary
        predicate: Dict with column, operator, value

    Returns:
        Boolean
    """
    col = predicate['column']
    op = predicate['operator']
    expected = predicate.get('value')
    actual = row.get(col)

    if op == 'IS NULL':
        return actual is None
    if op == 'IS NOT NULL':
        return actual is not None

    # NULL comparisons return False (SQL three-valued logic)
    if actual is None:
        return False

    if op == '=':
        return actual == expected
    elif op == '!=':
        return actual != expected
    elif op == '<':
        return actual < expected
    elif op == '>':
        return actual > expected
    elif op == '<=':
        return actual <= expected
    elif op == '>=':
        return actual >= expected
    elif op == 'IN':
        return actual in expected
    elif op == 'BETWEEN':
        return expected[0] <= actual <= expected[1]

    return False


def project_columns(rows, select_list):
    """Project specified columns from rows.

    Args:
        rows: List of row dicts
        select_list: List of column names (or '*' for all)

    Returns:
        List of projected row dicts
    """
    if '*' in select_list:
        return [dict(row) for row in rows]

    result = []
    for row in rows:
        projected = {}
        for col in select_list:
            projected[col] = row.get(col)
        result.append(projected)
    return result
