"""Analytical query engine pipeline.

Executes SQL-like queries defined in queries.json against inline table data.
Supports join-aggregate queries and window function queries.
"""

import json
import os
import sys

from data_loader import load_query_config
from join_engine import execute_join
from filter_engine import apply_where_clause
from aggregator import execute_aggregation
from window_functions import execute_window_function
from result_formatter import format_results

DATA_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"


def run_pipeline():
    """Load configuration and execute all defined queries."""
    config_path = os.path.join(DATA_DIR, "queries.json")
    config = load_query_config(config_path)

    tables = config["tables"]
    queries = config["queries"]

    results = []
    for query in queries:
        query_type = query["type"]
        if query_type == "join_aggregate":
            result = _execute_join_aggregate_query(query, tables)
        elif query_type == "window":
            result = _execute_window_query(query, tables)
        else:
            raise ValueError(f"Unknown query type: {query_type}")
        results.append({"query_id": query["id"], "data": result})

    output = format_results(results)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w") as f:
        json.dump(output, f, indent=2)

    return output


def _execute_join_aggregate_query(query, tables):
    """Execute a join followed by aggregation.

    Steps:
        1. Resolve left and right tables
        2. Perform the join operation
        3. Apply any post-join filters
        4. Execute aggregation with GROUP BY
    """
    join_spec = query["join"]
    left_table = tables[join_spec["left_table"]]
    right_table = tables[join_spec["right_table"]]

    joined = execute_join(left_table, right_table, join_spec)

    post_filter = query.get("filter")
    if post_filter:
        joined = apply_where_clause(joined, post_filter)

    group_by = query["group_by"]
    aggregations = query["aggregations"]

    return execute_aggregation(joined, group_by, aggregations)


def _execute_window_query(query, tables):
    """Execute a window function query.

    Steps:
        1. Resolve source table
        2. Apply optional pre-filter
        3. Execute window function over partitions
    """
    source = tables[query["source_table"]]

    pre_filter = query.get("filter")
    if pre_filter:
        source = apply_where_clause(source, pre_filter)

    window_spec = query["window"]
    return execute_window_function(source, window_spec)


if __name__ == "__main__":
    try:
        output = run_pipeline()
        print(f"Pipeline complete. {len(output['results'])} queries executed.")
        print(f"Output written to {OUTPUT_PATH}")
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        sys.exit(1)
