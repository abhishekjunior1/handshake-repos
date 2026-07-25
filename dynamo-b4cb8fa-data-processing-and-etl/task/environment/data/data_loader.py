"""
Data loader module for tabular transformation pipeline.

Loads transformation configuration and input data tables from JSON format.
Supports single-table and multi-table configurations.
"""

import json
import os
import sys


def load_config(config_path):
    """Load the transformation configuration file.

    The configuration specifies input tables, column mappings,
    join definitions, pivot operations, and derived columns.
    """
    if not os.path.exists(config_path):
        print(f"Error: Config not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    required = ['tables', 'operations']
    for key in required:
        if key not in config:
            print(f"Error: Missing '{key}' in config", file=sys.stderr)
            sys.exit(1)

    return config


def load_tables(config):
    """Extract table data from configuration.

    Each table has a name and a list of row dictionaries.
    Returns a dict mapping table_name to list of row dicts.
    """
    tables = {}
    for table_def in config['tables']:
        name = table_def['name']
        rows = table_def.get('rows', [])
        tables[name] = rows
    return tables


def get_operations(config):
    """Extract the ordered list of transformation operations.

    Operations are executed in sequence by the pipeline.
    Each operation has a 'type' and operation-specific parameters.
    """
    return config['operations']


def get_output_config(config):
    """Extract output formatting configuration.

    Specifies sort order, included columns, and output format.
    """
    return config.get('output', {
        'sort_by': None,
        'sort_order': 'descending',
        'columns': None
    })


def validate_table(table_name, rows):
    """Validate that a table has consistent column structure.

    All rows must have the same set of keys.
    """
    if not rows:
        return True

    expected_keys = set(rows[0].keys())
    for i, row in enumerate(rows[1:], 1):
        if set(row.keys()) != expected_keys:
            print(f"Warning: Row {i} in '{table_name}' has inconsistent columns",
                  file=sys.stderr)
            return False
    return True
