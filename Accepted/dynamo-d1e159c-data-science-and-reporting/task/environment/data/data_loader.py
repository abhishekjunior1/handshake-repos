"""Data Loader module for the EDA pipeline.

Loads tabular datasets from JSON format and provides column type
detection (numeric vs categorical) for downstream analysis modules.
"""

import json
from typing import Dict, List, Any, Optional


class DataLoadError(Exception):
    """Raised when data loading encounters an error."""
    pass


def load_dataset(filepath: str) -> Dict[str, Any]:
    """Load a dataset from JSON file.

    Expected format:
        {
            "columns": ["col1", "col2", ...],
            "data": [[val1, val2, ...], ...],
            "metadata": { "description": "...", ... }
        }

    Args:
        filepath: Path to the JSON dataset file.

    Returns:
        Dictionary with 'columns', 'data', and 'metadata' keys.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            dataset = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise DataLoadError(f"Failed to load dataset: {e}")

    if 'columns' not in dataset or 'data' not in dataset:
        raise DataLoadError("Dataset must have 'columns' and 'data' keys")

    return dataset


def detect_column_types(columns: List[str], data: List[List[Any]]
                        ) -> Dict[str, str]:
    """Detect whether each column is numeric or categorical.

    A column is numeric if >80% of non-null values are numeric.

    Args:
        columns: Column names.
        data: Row-oriented data.

    Returns:
        Dict mapping column name to 'numeric' or 'categorical'.
    """
    types = {}
    for col_idx, col_name in enumerate(columns):
        values = [row[col_idx] for row in data if row[col_idx] is not None]
        if not values:
            types[col_name] = 'categorical'
            continue

        numeric_count = sum(1 for v in values if isinstance(v, (int, float)))
        if numeric_count / len(values) > 0.8:
            types[col_name] = 'numeric'
        else:
            types[col_name] = 'categorical'

    return types


def get_column_values(data: List[List[Any]], columns: List[str],
                      col_name: str) -> List[Any]:
    """Extract values for a single column.

    Args:
        data: Row-oriented data.
        columns: Column names.
        col_name: Target column name.

    Returns:
        List of values for the specified column.
    """
    col_idx = columns.index(col_name)
    return [row[col_idx] for row in data]
