"""
Quality Scorer Module

Computes per-column and overall quality scores for validated datasets.
Uses statistical baselines (mean/stddev) to identify outlier values and
factors in constraint compliance to produce scores between 0.0 and 1.0.
"""

import math
from typing import Any, Dict, List, Optional, Tuple


def compute_threshold_stats(
    records: List[Dict[str, Any]], schema: Dict[str, Any]
) -> Dict[str, Dict[str, float]]:
    """Compute mean and standard deviation baselines for numeric columns.

    These statistics are used as thresholds for outlier detection during
    quality scoring. Values beyond 2 standard deviations from the mean
    are flagged as potential quality issues.

    Args:
        records: List of records to compute statistics from.
        schema: Schema definition with column type information.

    Returns:
        Dictionary mapping column names to their stats:
        {column_name: {"mean": float, "stddev": float, "count": int}}
    """
    stats = {}
    columns = schema.get("columns", [])

    numeric_columns = [
        col["name"] for col in columns
        if col.get("type") in ("int", "integer", "float", "number")
    ]

    for col_name in numeric_columns:
        values = []
        for record in records:
            if col_name in record and record[col_name] is not None:
                try:
                    values.append(float(record[col_name]))
                except (ValueError, TypeError):
                    continue

        if values:
            mean = sum(values) / len(values)
            variance = sum((v - mean) ** 2 for v in values) / len(values)
            stddev = math.sqrt(variance)
            stats[col_name] = {
                "mean": mean,
                "stddev": stddev,
                "count": len(values)
            }

    return stats


def compute_column_scores(
    records: List[Dict[str, Any]],
    schema: Dict[str, Any],
    threshold_stats: Dict[str, Dict[str, float]]
) -> Dict[str, float]:
    """Compute quality scores for each column in the schema.

    Scores are calculated based on:
    - Completeness: proportion of non-null values
    - Validity: proportion of values within statistical thresholds
    - Conformity: proportion of values matching declared types

    Args:
        records: List of validated records to score.
        schema: Schema definition with column information.
        threshold_stats: Statistical baselines for outlier detection.

    Returns:
        Dictionary mapping column names to their quality scores (0.0-1.0).
    """
    scores = {}
    columns = schema.get("columns", [])

    if not records:
        return {col["name"]: 0.0 for col in columns}

    total_records = len(records)

    for col_def in columns:
        col_name = col_def.get("name")
        col_type = col_def.get("type", "string")

        completeness_count = 0
        valid_count = 0

        for record in records:
            value = record.get(col_name)

            if value is not None:
                completeness_count += 1

                if _is_within_threshold(value, col_name, threshold_stats):
                    valid_count += 1
            else:
                if not col_def.get("required", False):
                    valid_count += 1

        completeness = completeness_count / total_records
        validity = valid_count / total_records

        score = round((completeness * 0.5) + (validity * 0.5), 4)
        scores[col_name] = min(1.0, max(0.0, score))

    return scores


def compute_overall_score(column_scores: Dict[str, float]) -> float:
    """Compute the overall dataset quality score from column scores.

    The overall score is the weighted average of all column scores,
    with equal weighting applied to each column.

    Args:
        column_scores: Dictionary mapping column names to their scores.

    Returns:
        Overall quality score as a float between 0.0 and 1.0.
    """
    if not column_scores:
        return 0.0

    total = sum(column_scores.values())
    overall = total / len(column_scores)

    return round(min(1.0, max(0.0, overall)), 4)


def _is_within_threshold(
    value: Any,
    column: str,
    threshold_stats: Dict[str, Dict[str, float]]
) -> bool:
    """Check if a value is within statistical thresholds.

    Values beyond 2 standard deviations from the mean are considered
    outliers. Non-numeric columns always pass this check.

    Args:
        value: The value to check.
        column: Column name for looking up threshold stats.
        threshold_stats: Pre-computed statistical baselines.

    Returns:
        True if value is within acceptable thresholds.
    """
    if column not in threshold_stats:
        return True

    try:
        num_value = float(value)
    except (ValueError, TypeError):
        return True

    stats = threshold_stats[column]
    mean = stats["mean"]
    stddev = stats["stddev"]

    if stddev == 0:
        return True

    z_score = abs(num_value - mean) / stddev
    return z_score <= 2.0
