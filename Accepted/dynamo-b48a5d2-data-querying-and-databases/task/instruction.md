You are debugging an analytical query engine that executes SQL-like queries against in-memory table data. The engine processes a `queries.json` configuration file containing inline table definitions and query specifications, then writes results to `/app/output.json`.

The pipeline is implemented across these modules in `/app/`:

- `pipeline.py` — Main orchestrator. Loads config, dispatches queries by type, writes output.
- `data_loader.py` — Parses `queries.json`, extracts tables into row-oriented dictionaries.
- `join_engine.py` — Implements INNER and LEFT JOIN with column prefixing to avoid collisions.
- `filter_engine.py` — Evaluates WHERE conditions (comparison operators, AND logic).
- `aggregator.py` — GROUP BY with aggregate functions (COUNT, SUM, AVG, MIN, MAX).
- `window_functions.py` — Window functions (RUNNING_TOTAL, RANK) over partitioned/ordered data.
- `result_formatter.py` — Formats results as JSON with execution metadata.

Run the pipeline with: `python3 pipeline.py`

The engine supports two query types defined in `queries.json`:

1. `join_aggregate` — Joins two tables, optionally filters, then groups and aggregates.
2. `window` — Applies a window function (cumulative sum or rank) over partitioned rows.

The current `queries.json` contains sample e-commerce data (orders, order lines, customers) and three queries. The pipeline produces correct output on this data. However, the engine contains bugs that produce incorrect results when the data has different characteristics. Your task is to identify and fix these bugs so the pipeline produces correct output on any valid input data.

Do not rewrite the pipeline from scratch. Fix the existing code in place.

The output file (`/app/output.json`) must conform to this schema:

```json
{
  "metadata": {
    "executed_at": "<ISO timestamp>",
    "query_count": <int>,
    "engine_version": "1.0.0"
  },
  "results": [
    {
      "query_id": "<string>",
      "row_count": <int>,
      "columns": ["<col1>", "<col2>", ...],
      "rows": [{"<col1>": <val>, "<col2>": <val>, ...}, ...]
    }
  ]
}
```

Each query result includes its ID, the count of output rows, column names, and the row data as a list of dictionaries. The metadata section records execution timestamp, number of queries processed, and engine version.
