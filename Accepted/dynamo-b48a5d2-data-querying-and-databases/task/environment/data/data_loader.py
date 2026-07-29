"""Data loader module.

Loads query configuration from queries.json including inline table definitions
and query specifications. Tables are stored as lists of dictionaries (row-oriented).
"""

import json
import os
from typing import Any


def load_query_config(config_path: str) -> dict[str, Any]:
    """Load and validate the query configuration file.

    Args:
        config_path: Path to queries.json

    Returns:
        Dictionary with 'tables' and 'queries' keys.
        Tables are dict[str, list[dict]] mapping table name to rows.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    with open(config_path, "r") as f:
        raw_config = json.load(f)

    tables = _extract_tables(raw_config.get("tables", {}))
    queries = _validate_queries(raw_config.get("queries", []))

    return {"tables": tables, "queries": queries}


def _extract_tables(raw_tables: dict) -> dict[str, list[dict]]:
    """Extract table definitions into row-oriented format.

    Each table in the config has a 'columns' list and 'rows' list-of-lists.
    Convert to list of dictionaries for easier processing.
    """
    tables = {}
    for table_name, table_def in raw_tables.items():
        columns = table_def["columns"]
        rows = table_def["rows"]
        tables[table_name] = [
            dict(zip(columns, row)) for row in rows
        ]
    return tables


def _validate_queries(queries: list[dict]) -> list[dict]:
    """Validate query definitions have required fields."""
    validated = []
    for i, query in enumerate(queries):
        if "id" not in query:
            raise ValueError(f"Query at index {i} missing 'id' field")
        if "type" not in query:
            raise ValueError(f"Query '{query['id']}' missing 'type' field")

        query_type = query["type"]
        if query_type == "join_aggregate":
            _validate_join_aggregate(query)
        elif query_type == "window":
            _validate_window(query)
        else:
            raise ValueError(f"Unknown query type: {query_type}")

        validated.append(query)
    return validated


def _validate_join_aggregate(query: dict) -> None:
    """Validate join_aggregate query has required fields."""
    required = ["join", "group_by", "aggregations"]
    for field in required:
        if field not in query:
            raise ValueError(f"Query '{query['id']}' missing '{field}'")

    join = query["join"]
    for field in ["left_table", "right_table", "type", "left_on", "right_on"]:
        if field not in join:
            raise ValueError(f"Query '{query['id']}' join missing '{field}'")


def _validate_window(query: dict) -> None:
    """Validate window query has required fields."""
    required = ["source_table", "window"]
    for field in required:
        if field not in query:
            raise ValueError(f"Query '{query['id']}' missing '{field}'")

    window = query["window"]
    for field in ["function", "order_by"]:
        if field not in window:
            raise ValueError(f"Query '{query['id']}' window missing '{field}'")
