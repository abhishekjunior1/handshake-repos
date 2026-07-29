"""
Column mapper module for tabular transformation pipeline.

Handles column renaming and type coercion operations on tabular data.
"""


def rename_columns(rows, column_map):
    """Rename columns in all rows according to the mapping.

    Args:
        rows: list of row dicts
        column_map: dict mapping old_name -> new_name

    Returns:
        New list of row dicts with renamed columns.
    """
    if not column_map:
        return rows

    result = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            new_key = column_map.get(key, key)
            new_row[new_key] = value
        result.append(new_row)
    return result


def apply_type_coercion(rows, type_map):
    """Apply type coercion to specified columns.

    Supported types: 'float', 'int', 'string', 'bool'.
    Values that cannot be coerced are left as-is.

    Args:
        rows: list of row dicts
        type_map: dict mapping column_name -> target_type

    Returns:
        New list of row dicts with coerced values.
    """
    if not type_map:
        return rows

    result = []
    for row in rows:
        new_row = {}
        for key, value in row.items():
            if key in type_map:
                new_row[key] = _coerce_value(value, type_map[key])
            else:
                new_row[key] = value
        result.append(new_row)
    return result


def select_columns(rows, columns):
    """Select only specified columns from each row.

    Args:
        rows: list of row dicts
        columns: list of column names to keep

    Returns:
        New list of row dicts with only selected columns.
    """
    if not columns:
        return rows

    result = []
    for row in rows:
        new_row = {col: row.get(col, None) for col in columns}
        result.append(new_row)
    return result


def add_constant_column(rows, column_name, value):
    """Add a column with a constant value to all rows.

    Args:
        rows: list of row dicts
        column_name: name for the new column
        value: constant value for all rows

    Returns:
        New list of row dicts with added column.
    """
    result = []
    for row in rows:
        new_row = dict(row)
        new_row[column_name] = value
        result.append(new_row)
    return result


def _coerce_value(value, target_type):
    """Coerce a single value to the target type."""
    if value is None:
        return None

    try:
        if target_type == 'float':
            return float(value)
        elif target_type == 'int':
            # Convert through float first to handle decimal strings
            return int(float(value))
        elif target_type == 'string':
            return str(value)
        elif target_type == 'bool':
            if isinstance(value, str):
                return value.lower() in ('true', '1', 'yes')
            return bool(value)
    except (ValueError, TypeError):
        return value

    return value
