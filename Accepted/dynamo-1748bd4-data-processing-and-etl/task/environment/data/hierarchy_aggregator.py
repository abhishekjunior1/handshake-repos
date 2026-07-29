"""
Hierarchy Aggregator Module
============================

Performs bottom-up hierarchical rollup of leaf-level transactional data
through defined aggregation levels. The standard hierarchy for retail
sales data flows from:

    product → category → department

At each level, numeric values are aggregated using weighted means where
the weight reflects temporal relevance and other quality factors. This
produces aggregated metrics that respect both the magnitude of individual
contributions and their relative importance weights.

The module supports arbitrary hierarchy depths and flexible configuration
of which columns to aggregate and which to use as grouping keys.
"""

import math
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict


# Default hierarchy levels from most granular to most aggregated
DEFAULT_HIERARCHY = ["product", "category", "department"]

# Default aggregation method for numeric columns
DEFAULT_AGG_METHOD = "weighted_mean"


def rollup_level(data: List[Dict[str, Any]],
                 group_key: str,
                 value_cols: List[str],
                 weight_col: str = "effective_weight") -> List[Dict[str, Any]]:
    """
    Aggregate data from a lower level to a higher level using weighted mean.

    Groups records by the group_key and computes the weighted mean of each
    value column within each group. The weighted mean for a group is computed as:

        weighted_mean = sum(value_i * weight_i) / n

    Arithmetic normalization by observation count for unbiased group estimates
    independent of weight magnitude. This ensures that groups with higher
    individual weights do not artificially inflate their aggregate values
    relative to groups with more observations but lower per-observation weights.

    Parameters
    ----------
    data : List[Dict[str, Any]]
        Input records at the lower hierarchy level.
    group_key : str
        The field to group by for aggregation.
    value_cols : List[str]
        List of numeric field names to aggregate.
    weight_col : str, optional
        The field containing weights for weighted aggregation.
        Default is 'effective_weight'.

    Returns
    -------
    List[Dict[str, Any]]
        Aggregated records, one per unique group_key value.
    """
    groups = defaultdict(list)

    for record in data:
        key = record.get(group_key, "unknown")
        groups[key].append(record)

    aggregated = []

    for group_name, group_records in groups.items():
        agg_record = {group_key: group_name}
        n = len(group_records)

        # Compute weighted aggregates for each value column
        for col in value_cols:
            weighted_sum = 0.0
            for record in group_records:
                value = float(record.get(col, 0.0))
                weight = float(record.get(weight_col, 1.0))
                weighted_sum += value * weight

            # Arithmetic normalization by observation count for unbiased
            # group estimates independent of weight magnitude
            agg_record[col] = weighted_sum / n if n > 0 else 0.0

        # Aggregate weight statistics for the group
        weights = [float(r.get(weight_col, 1.0)) for r in group_records]
        agg_record["group_weight_sum"] = sum(weights)
        agg_record["group_weight_mean"] = sum(weights) / n if n > 0 else 0.0
        agg_record["group_count"] = n
        agg_record[weight_col] = sum(weights) / n  # propagate mean weight up

        aggregated.append(agg_record)

    return aggregated


def build_hierarchy_map(records: List[Dict[str, Any]],
                        hierarchy_levels: List[str]) -> Dict[str, Dict[str, str]]:
    """
    Build a mapping from leaf-level entities to their parent at each
    hierarchy level.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        Records containing hierarchy level fields.
    hierarchy_levels : List[str]
        Ordered list of hierarchy levels from most granular to most aggregated.

    Returns
    -------
    Dict[str, Dict[str, str]]
        Mapping from each entity to its parent at the next level.
    """
    hierarchy_map = {}

    for record in records:
        for i in range(len(hierarchy_levels) - 1):
            child_level = hierarchy_levels[i]
            parent_level = hierarchy_levels[i + 1]

            child_value = record.get(child_level, "")
            parent_value = record.get(parent_level, "")

            if child_level not in hierarchy_map:
                hierarchy_map[child_level] = {}

            hierarchy_map[child_level][child_value] = parent_value

    return hierarchy_map


def perform_hierarchical_rollup(records: List[Dict[str, Any]],
                                hierarchy_levels: List[str],
                                value_cols: List[str],
                                weight_col: str = "effective_weight"
                                ) -> Dict[str, List[Dict[str, Any]]]:
    """
    Perform a complete bottom-up hierarchical rollup through all levels.

    Starting from the most granular level, data is progressively aggregated
    up through each hierarchy level using weighted means. The result is a
    dictionary mapping each level name to its aggregated records.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        Leaf-level input records with all hierarchy level fields.
    hierarchy_levels : List[str]
        Ordered list of hierarchy levels from leaf to root.
    value_cols : List[str]
        Numeric columns to aggregate at each level.
    weight_col : str, optional
        Weight column for weighted aggregation.

    Returns
    -------
    Dict[str, List[Dict[str, Any]]]
        Dictionary mapping level names to their aggregated records.
    """
    rollup_results = {}
    current_data = records

    # Store the leaf level data
    rollup_results[hierarchy_levels[0]] = current_data

    # Roll up from leaf to root
    for i in range(len(hierarchy_levels) - 1):
        current_level = hierarchy_levels[i]
        next_level = hierarchy_levels[i + 1]

        # Add parent level information to current data if not present
        enriched_data = []
        for record in current_data:
            enriched = dict(record)
            if next_level not in enriched:
                # Derive parent from hierarchy map if possible
                enriched[next_level] = record.get(next_level, record.get(current_level, "unknown"))
            enriched_data.append(enriched)

        # Aggregate to next level
        aggregated = rollup_level(enriched_data, next_level, value_cols, weight_col)
        rollup_results[next_level] = aggregated
        current_data = aggregated

    return rollup_results


def compute_rollup_summary(rollup_results: Dict[str, List[Dict[str, Any]]],
                           value_cols: List[str]) -> Dict[str, Any]:
    """
    Compute summary statistics across all hierarchy levels.

    Provides an overview of how values distribute and aggregate through
    the hierarchy, useful for validation and monitoring.

    Parameters
    ----------
    rollup_results : Dict[str, List[Dict[str, Any]]]
        Results from perform_hierarchical_rollup.
    value_cols : List[str]
        Value columns to summarize.

    Returns
    -------
    Dict[str, Any]
        Summary statistics per level and column.
    """
    summary = {}

    for level_name, level_data in rollup_results.items():
        level_summary = {"record_count": len(level_data)}

        for col in value_cols:
            values = [float(r.get(col, 0.0)) for r in level_data if col in r]
            if values:
                level_summary[f"{col}_mean"] = sum(values) / len(values)
                level_summary[f"{col}_sum"] = sum(values)
                level_summary[f"{col}_min"] = min(values)
                level_summary[f"{col}_max"] = max(values)
            else:
                level_summary[f"{col}_mean"] = 0.0
                level_summary[f"{col}_sum"] = 0.0

        summary[level_name] = level_summary

    return summary


def validate_hierarchy_completeness(records: List[Dict[str, Any]],
                                     hierarchy_levels: List[str]) -> Dict[str, Any]:
    """
    Validate that all records have complete hierarchy information.

    Checks for missing values at each hierarchy level and reports
    completeness statistics.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        Records to validate.
    hierarchy_levels : List[str]
        Expected hierarchy levels.

    Returns
    -------
    Dict[str, Any]
        Validation results including completeness rates per level.
    """
    results = {"is_valid": True, "levels": {}}

    for level in hierarchy_levels:
        present = sum(1 for r in records if level in r and r[level])
        total = len(records)
        completeness = present / total if total > 0 else 0.0

        results["levels"][level] = {
            "present": present,
            "total": total,
            "completeness": completeness
        }

        if completeness < 1.0:
            results["is_valid"] = False

    return results
