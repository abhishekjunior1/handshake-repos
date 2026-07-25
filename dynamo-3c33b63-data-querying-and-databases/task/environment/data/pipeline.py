"""Analytical query engine pipeline.

Orchestrates query execution across data loading, filtering,
aggregation, window functions, joins, and result formatting.
"""

import json
import sys

from data_loader import load_query_config, extract_tables
from filter_engine import apply_where_clause
from aggregator import execute_aggregation
from window_functions import apply_window_functions
from join_engine import execute_join
from result_formatter import format_query_result, build_output, build_metadata


def run_pipeline(config_path: str, output_path: str) -> None:
    """Execute the full analytical query pipeline."""
    config = load_query_config(config_path)
    tables = extract_tables(config)
    metadata = build_metadata(config, tables)

    results = []
    for i, query in enumerate(config["queries"]):
        result = execute_query(query, tables, i)
        results.append(result)

    output = build_output(results, metadata)

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)


def execute_query(query: dict, tables: dict, query_index: int) -> dict:
    """Execute a single query against the loaded tables."""
    query_type = query["type"]

    if query_type == "aggregate":
        rows = _execute_aggregate_query(query, tables)
    elif query_type == "window":
        rows = _execute_window_query(query, tables)
    elif query_type == "join_aggregate":
        rows = _execute_join_aggregate_query(query, tables)
    else:
        raise ValueError(f"Unknown query type: {query_type}")

    return format_query_result(rows, query, query_index)


def _execute_aggregate_query(query: dict, tables: dict) -> list[dict]:
    """Execute an aggregation query with GROUP BY."""
    source_table = query["source_table"]
    rows = tables[source_table][:]

    where_clause = query.get("where")
    if where_clause:
        rows = apply_where_clause(rows, where_clause)

    group_by = query.get("group_by", [])
    aggregations = query.get("aggregations", [])
    having_clause = query.get("having")

    return execute_aggregation(rows, group_by, aggregations, having_clause)


def _execute_window_query(query: dict, tables: dict) -> list[dict]:
    """Execute a window function query with partition and ordering."""
    source_table = query["source_table"]
    rows = tables[source_table][:]

    where_clause = query.get("where")
    if where_clause:
        rows = apply_where_clause(rows, where_clause)

    window_specs = query.get("window_functions", [])
    rows = apply_window_functions(rows, window_specs)

    return rows


def _execute_join_aggregate_query(query: dict, tables: dict) -> list[dict]:
    """Execute a join followed by aggregation.

    Joins the specified tables, then computes aggregate functions
    over the joined result set grouped by the specified columns.
    """
    source_table = query["source_table"]
    join_spec = query["join"]
    target_table = join_spec["table"]

    left_rows = tables[source_table][:]
    right_rows = tables[target_table][:]

    # Apply join with filter conditions
    join_filter = join_spec.get("filter")
    joined = execute_join(left_rows, right_rows, join_spec)

    # Apply filter condition from join spec as WHERE on joined result
    if join_filter:
        joined = apply_where_clause(joined, join_filter)

    # Aggregate over the joined result
    group_by = query.get("group_by", [])
    aggregations = query.get("aggregations", [])

    return execute_aggregation(joined, group_by, aggregations)


if __name__ == "__main__":
    config_file = "/app/queries.json"
    output_file = "/app/output.json"

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    run_pipeline(config_file, output_file)
