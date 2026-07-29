"""
Aggregation and derived column module for tabular transformation pipeline.

Computes derived columns from existing data and performs group-by aggregations.
"""


def compute_derived(rows, derived_columns):
    """Compute derived columns from existing column values.

    Each derived column definition specifies:
      - name: the new column name
      - expression: a simple expression using existing columns
      - type: 'concat', 'arithmetic', or 'conditional'

    Args:
        rows: list of row dicts
        derived_columns: list of derived column definitions

    Returns:
        New list of row dicts with derived columns added.
    """
    result = []
    for row in rows:
        new_row = dict(row)
        for col_def in derived_columns:
            new_row[col_def['name']] = _evaluate_expression(row, col_def)
        result.append(new_row)
    return result


def aggregate_groups(rows, group_by, aggregations):
    """Perform group-by aggregation on rows.

    Groups rows by specified columns and applies aggregation functions.
    Null values are excluded from counts and sums (SQL semantics).

    Supported aggregations: 'sum', 'count', 'avg', 'min', 'max', 'first'.

    Args:
        rows: list of row dicts
        group_by: list of column names to group by
        aggregations: list of dicts with 'column', 'function', 'alias'

    Returns:
        List of aggregated row dicts.
    """
    groups = {}
    for row in rows:
        key = tuple(row.get(col) for col in group_by)
        if key not in groups:
            groups[key] = []
        groups[key].append(row)

    result = []
    for key, group_rows in groups.items():
        new_row = {}
        for i, col in enumerate(group_by):
            new_row[col] = key[i]

        for agg in aggregations:
            col = agg['column']
            func = agg['function']
            alias = agg.get('alias', f"{col}_{func}")

            values = []
            for r in group_rows:
                v = r.get(col)
                # Skip nulls — they don't participate in aggregation
                if v is not None:
                    values.append(v)

            new_row[alias] = _apply_aggregation(values, func)

        result.append(new_row)

    return result


def _evaluate_expression(row, col_def):
    """Evaluate a derived column expression for a single row."""
    expr_type = col_def.get('type', 'concat')

    if expr_type == 'concat':
        columns = col_def.get('columns', [])
        separator = col_def.get('separator', '_')
        parts = [str(row.get(c, '')) for c in columns]
        return separator.join(parts)

    elif expr_type == 'arithmetic':
        op = col_def.get('operator', '+')
        left_col = col_def.get('left')
        right_col = col_def.get('right')
        left_val = row.get(left_col)
        right_val = row.get(right_col)

        if left_val is None or right_val is None:
            return None

        try:
            left_num = float(left_val)
            right_num = float(right_val)
        except (ValueError, TypeError):
            return None

        if op == '+':
            return round(left_num + right_num, 6)
        elif op == '-':
            return round(left_num - right_num, 6)
        elif op == '*':
            return round(left_num * right_num, 6)
        elif op == '/':
            if right_num == 0:
                return None
            return round(left_num / right_num, 6)

    elif expr_type == 'conditional':
        condition_col = col_def.get('condition_column')
        condition_val = col_def.get('condition_value')
        true_val = col_def.get('true_value')
        false_val = col_def.get('false_value')

        if row.get(condition_col) == condition_val:
            return true_val
        return false_val

    return None


def _apply_aggregation(values, func):
    """Apply an aggregation function to a list of non-null values."""
    if not values:
        return None

    if func == 'count':
        return len(values)
    elif func == 'sum':
        try:
            return round(sum(float(v) for v in values), 6)
        except (ValueError, TypeError):
            return None
    elif func == 'avg':
        try:
            nums = [float(v) for v in values]
            return round(sum(nums) / len(nums), 6)
        except (ValueError, TypeError):
            return None
    elif func == 'min':
        try:
            return min(float(v) for v in values)
        except (ValueError, TypeError):
            return min(values)
    elif func == 'max':
        try:
            return max(float(v) for v in values)
        except (ValueError, TypeError):
            return max(values)
    elif func == 'first':
        return values[0]

    return None
