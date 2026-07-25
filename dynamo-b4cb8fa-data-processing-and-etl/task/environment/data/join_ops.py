"""
Join and merge operations for tabular transformation pipeline.

Implements table join operations including inner, left, and full outer joins.
"""


def merge_tables(left_rows, right_rows, left_key, right_key, how='left'):
    """Merge two tables on specified key columns.

    Args:
        left_rows: list of row dicts for left table
        right_rows: list of row dicts for right table
        left_key: column name in left table to join on
        right_key: column name in right table to join on
        how: join type - 'inner', 'left', or 'outer'

    Returns:
        List of merged row dicts.
    """
    if not left_rows:
        return []

    right_index = _build_index(right_rows, right_key)

    result = []
    matched_right_keys = set()

    for left_row in left_rows:
        join_value = left_row.get(left_key)
        matching_right = right_index.get(join_value, [])

        if matching_right:
            for right_row in matching_right:
                merged = _merge_rows(left_row, right_row, right_key)
                result.append(merged)
                matched_right_keys.add(join_value)
        elif how in ('left', 'outer'):
            right_cols = _get_right_columns(right_rows, right_key)
            padded = dict(left_row)
            for col in right_cols:
                padded[col] = None
            result.append(padded)

    if how == 'outer':
        for right_row in right_rows:
            rkey_val = right_row.get(right_key)
            if rkey_val not in matched_right_keys:
                left_cols = _get_left_columns(left_rows, left_key)
                padded = {col: None for col in left_cols}
                padded.update({k: v for k, v in right_row.items() if k != right_key})
                padded[left_key] = rkey_val
                result.append(padded)

    return result


def _build_index(rows, key_col):
    """Build a lookup index from rows keyed by a column value."""
    index = {}
    for row in rows:
        key_val = row.get(key_col)
        if key_val not in index:
            index[key_val] = []
        index[key_val].append(row)
    return index


def _merge_rows(left_row, right_row, right_key):
    """Merge a left row with a right row, dropping the right join key column."""
    merged = dict(left_row)
    for key, value in right_row.items():
        if key != right_key:
            merged[key] = value
    return merged


def _get_right_columns(right_rows, right_key):
    """Get column names from right table excluding the join key."""
    if not right_rows:
        return []
    return [col for col in right_rows[0].keys() if col != right_key]


def _get_left_columns(left_rows, left_key):
    """Get all column names from left table."""
    if not left_rows:
        return []
    return list(left_rows[0].keys())


def concatenate_tables(tables_list):
    """Concatenate multiple tables vertically (union all).

    All tables should have the same columns. Missing columns
    are filled with None.

    Args:
        tables_list: list of row-list tables

    Returns:
        Single concatenated list of row dicts.
    """
    if not tables_list:
        return []

    all_cols = set()
    for table in tables_list:
        for row in table:
            all_cols.update(row.keys())

    result = []
    for table in tables_list:
        for row in table:
            padded = {col: row.get(col, None) for col in all_cols}
            result.append(padded)

    return result
