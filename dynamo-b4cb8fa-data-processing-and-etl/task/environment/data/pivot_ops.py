"""
Pivot and unpivot operations for tabular transformation pipeline.

Handles reshaping of tabular data between wide and long formats.
"""


def pivot_table(rows, index_col, pivot_col, value_col, aggfunc='first'):
    """Pivot rows from long to wide format.

    Groups rows by index_col, creates new columns from unique values
    in pivot_col, and fills cells with values from value_col.

    When multiple rows share the same (index, pivot) combination,
    the first encountered value is used as the representative value
    for that cell.

    Args:
        rows: list of row dicts
        index_col: column to use as row index
        pivot_col: column whose values become new column names
        value_col: column containing cell values
        aggfunc: aggregation function for duplicate keys ('first')

    Returns:
        List of pivoted row dicts.
    """
    if not rows:
        return []

    pivot_values = []
    for row in rows:
        val = row.get(pivot_col)
        if val not in pivot_values:
            pivot_values.append(val)

    groups = {}
    for row in rows:
        idx = row.get(index_col)
        pval = row.get(pivot_col)
        vval = row.get(value_col)

        if idx not in groups:
            groups[idx] = {}

        # Use first value encountered for each (index, pivot) pair
        if pval not in groups[idx]:
            groups[idx][pval] = vval

    result = []
    for idx in groups:
        new_row = {index_col: idx}
        for pval in pivot_values:
            new_row[pval] = groups[idx].get(pval, None)
        result.append(new_row)

    return result


def unpivot_table(rows, id_cols, value_cols, var_name='variable', value_name='value'):
    """Unpivot (melt) rows from wide to long format.

    Keeps id_cols fixed and unpivots value_cols into two new columns:
    one for the variable name and one for the value.

    Args:
        rows: list of row dicts
        id_cols: columns to keep as identifiers
        value_cols: columns to unpivot
        var_name: name for the new variable column
        value_name: name for the new value column

    Returns:
        List of unpivoted row dicts.
    """
    if not rows:
        return []

    result = []
    for row in rows:
        for col in value_cols:
            new_row = {}
            for id_col in id_cols:
                new_row[id_col] = row.get(id_col)
            new_row[var_name] = col
            new_row[value_name] = row.get(col, None)
            result.append(new_row)

    return result


def pivot_with_multiple_values(rows, index_col, pivot_col, value_cols):
    """Pivot with multiple value columns.

    Creates new columns named '{pivot_value}_{value_col}' for each
    combination of pivot value and value column.

    Args:
        rows: list of row dicts
        index_col: column to use as row index
        pivot_col: column whose values become column name prefixes
        value_cols: list of columns to include as values

    Returns:
        List of pivoted row dicts.
    """
    if not rows:
        return []

    pivot_values = []
    for row in rows:
        val = row.get(pivot_col)
        if val not in pivot_values:
            pivot_values.append(val)

    groups = {}
    for row in rows:
        idx = row.get(index_col)
        pval = row.get(pivot_col)

        if idx not in groups:
            groups[idx] = {}

        if pval not in groups[idx]:
            groups[idx][pval] = {vc: row.get(vc) for vc in value_cols}

    result = []
    for idx in groups:
        new_row = {index_col: idx}
        for pval in pivot_values:
            for vc in value_cols:
                col_name = f"{pval}_{vc}"
                new_row[col_name] = groups[idx].get(pval, {}).get(vc, None)
        result.append(new_row)

    return result
