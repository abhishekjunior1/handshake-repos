"""
Data Loader Module

Handles loading and parsing of JSON dataset files and schema definitions.
Provides functions to read raw data from disk and transform it into
structured table representations for downstream validation.
"""

import json
import os
from typing import Any, Dict, List, Optional


def load_dataset(path: str) -> Dict[str, Any]:
    """Load a JSON dataset from the specified file path.

    Args:
        path: Absolute or relative path to the dataset JSON file.

    Returns:
        Parsed JSON content as a dictionary.

    Raises:
        FileNotFoundError: If the dataset file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Dataset file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return data


def load_schema(path: str) -> Dict[str, Any]:
    """Load a JSON schema definition from the specified file path.

    Args:
        path: Absolute or relative path to the schema JSON file.

    Returns:
        Parsed schema definition as a dictionary.

    Raises:
        FileNotFoundError: If the schema file does not exist.
        json.JSONDecodeError: If the file contains invalid JSON.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(f"Schema file not found: {path}")

    with open(path, "r", encoding="utf-8") as f:
        schema = json.load(f)

    return schema


def parse_tables(raw_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
    """Parse raw dataset into named tables with their records.

    Supports two dataset formats:
    1. Multi-table: {"tables": {"table_name": {"records": [...]}}}
    2. Single-table: {"name": "...", "records": [...]}

    Args:
        raw_data: Raw parsed JSON data from load_dataset.

    Returns:
        Dictionary mapping table names to lists of record dictionaries.
    """
    tables = {}

    if "tables" in raw_data:
        for table_name, table_data in raw_data["tables"].items():
            records = table_data.get("records", [])
            tables[table_name] = records
    elif "records" in raw_data:
        table_name = raw_data.get("name", "default")
        tables[table_name] = raw_data["records"]
    else:
        raise ValueError(
            "Invalid dataset format: expected 'tables' or 'records' key"
        )

    return tables


def get_dataset_metadata(raw_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract metadata from the raw dataset.

    Args:
        raw_data: Raw parsed JSON data from load_dataset.

    Returns:
        Dictionary containing dataset metadata (name, version, etc.).
    """
    metadata = {
        "name": raw_data.get("name", "unnamed_dataset"),
        "version": raw_data.get("version", "1.0"),
        "description": raw_data.get("description", ""),
    }

    return metadata


def get_table_names(raw_data: Dict[str, Any]) -> List[str]:
    """Get list of table names from the dataset.

    Args:
        raw_data: Raw parsed JSON data from load_dataset.

    Returns:
        List of table name strings.
    """
    if "tables" in raw_data:
        return list(raw_data["tables"].keys())
    elif "records" in raw_data:
        return [raw_data.get("name", "default")]
    return []
