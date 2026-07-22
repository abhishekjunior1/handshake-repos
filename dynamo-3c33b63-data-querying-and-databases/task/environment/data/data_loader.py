"""Data loader module for the analytical query engine.

Loads tabular data from JSON files representing database tables,
validates schemas, and provides access to table metadata.
"""

import json
import sys
from typing import Any


def load_query_config(config_path: str) -> dict:
    """Load query configuration from JSON file."""
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in configuration: {e}")
        sys.exit(1)

    _validate_config(config)
    return config


def _validate_config(config: dict) -> None:
    """Validate the query configuration structure."""
    required_keys = ["tables", "queries"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Configuration missing required key: {key}")

    if not isinstance(config["tables"], dict):
        raise ValueError("'tables' must be a dictionary of table definitions")

    if not isinstance(config["queries"], list):
        raise ValueError("'queries' must be a list of query definitions")

    for table_name, table_def in config["tables"].items():
        _validate_table(table_name, table_def)

    for i, query in enumerate(config["queries"]):
        _validate_query(i, query)


def _validate_table(name: str, table_def: dict) -> None:
    """Validate a single table definition."""
    if "columns" not in table_def:
        raise ValueError(f"Table '{name}' missing 'columns' definition")
    if "rows" not in table_def:
        raise ValueError(f"Table '{name}' missing 'rows' data")

    columns = table_def["columns"]
    if not isinstance(columns, list) or len(columns) == 0:
        raise ValueError(f"Table '{name}' must have at least one column")

    for row_idx, row in enumerate(table_def["rows"]):
        if len(row) != len(columns):
            raise ValueError(
                f"Table '{name}' row {row_idx}: expected {len(columns)} "
                f"values, got {len(row)}"
            )


def _validate_query(index: int, query: dict) -> None:
    """Validate a single query definition."""
    required = ["type", "source_table", "select"]
    for key in required:
        if key not in query:
            raise ValueError(f"Query {index} missing required key: '{key}'")

    valid_types = ["aggregate", "window", "join", "join_aggregate"]
    if query["type"] not in valid_types:
        raise ValueError(
            f"Query {index} has invalid type '{query['type']}'. "
            f"Valid types: {valid_types}"
        )


def build_table(table_def: dict) -> list[dict[str, Any]]:
    """Convert raw table definition into list of row dictionaries."""
    columns = table_def["columns"]
    rows = []
    for raw_row in table_def["rows"]:
        row_dict = {}
        for col_idx, col_name in enumerate(columns):
            row_dict[col_name] = raw_row[col_idx]
        rows.append(row_dict)
    return rows


def get_column_types(table_def: dict, rows: list[dict]) -> dict[str, str]:
    """Infer column types from the first non-null value in each column."""
    columns = table_def["columns"]
    col_types = {}
    for col in columns:
        col_types[col] = "null"
        for row in rows:
            val = row[col]
            if val is not None:
                if isinstance(val, bool):
                    col_types[col] = "boolean"
                elif isinstance(val, int):
                    col_types[col] = "integer"
                elif isinstance(val, float):
                    col_types[col] = "numeric"
                else:
                    col_types[col] = "string"
                break
    return col_types


def extract_tables(config: dict) -> dict[str, list[dict[str, Any]]]:
    """Extract all tables from config into usable row-dictionary format."""
    tables = {}
    for table_name, table_def in config["tables"].items():
        tables[table_name] = build_table(table_def)
    return tables
