"""
Output writer module for tabular transformation pipeline.

Formats transformed data and writes structured JSON output.
Handles sorting, column selection, and final formatting.
"""

import json


def sort_rows(rows, sort_by, sort_order='descending'):
    """Sort rows by a specified column.

    Args:
        rows: list of row dicts
        sort_by: column name to sort by
        sort_order: 'ascending' or 'descending'

    Returns:
        New sorted list of row dicts.
    """
    if not sort_by or not rows:
        return rows

    def sort_key(row):
        val = row.get(sort_by)
        if val is None:
            return (1, '')
        if isinstance(val, (int, float)):
            return (0, val)
        return (0, str(val))

    reverse = (sort_order == 'descending')
    return sorted(rows, key=sort_key, reverse=reverse)


def format_output(rows, metadata):
    """Format the final output structure.

    Args:
        rows: list of transformed row dicts
        metadata: dict with transformation metadata

    Returns:
        Complete output dictionary ready for JSON serialization.
    """
    return {
        'metadata': {
            'row_count': len(rows),
            'columns': list(rows[0].keys()) if rows else [],
            'transformations_applied': metadata.get('transformations', []),
            'source_tables': metadata.get('source_tables', [])
        },
        'data': rows
    }


def write_output(output, output_path):
    """Write the output dictionary to a JSON file.

    Args:
        output: complete output dictionary
        output_path: file path to write to
    """
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, sort_keys=False)


def filter_rows(rows, filter_col, filter_value, operator='eq'):
    """Filter rows based on a column condition.

    Args:
        rows: list of row dicts
        filter_col: column to filter on
        filter_value: value to compare against
        operator: 'eq', 'ne', 'gt', 'lt', 'gte', 'lte', 'contains'

    Returns:
        Filtered list of row dicts.
    """
    result = []
    for row in rows:
        val = row.get(filter_col)
        if _matches_filter(val, filter_value, operator):
            result.append(row)
    return result


def _matches_filter(val, filter_value, operator):
    """Check if a value matches a filter condition."""
    if val is None:
        return False

    if operator == 'eq':
        return val == filter_value
    elif operator == 'ne':
        return val != filter_value
    elif operator == 'contains':
        return str(filter_value) in str(val)

    try:
        num_val = float(val)
        num_filter = float(filter_value)
        if operator == 'gt':
            return num_val > num_filter
        elif operator == 'lt':
            return num_val < num_filter
        elif operator == 'gte':
            return num_val >= num_filter
        elif operator == 'lte':
            return num_val <= num_filter
    except (ValueError, TypeError):
        return False

    return False
