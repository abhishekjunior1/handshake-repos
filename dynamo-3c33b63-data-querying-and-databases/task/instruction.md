An analytical query engine pipeline at `/app/pipeline.py` executes structured queries against JSON-based tabular data. It uses modules `/app/data_loader.py`, `/app/filter_engine.py`, `/app/aggregator.py`, `/app/window_functions.py`, `/app/join_engine.py`, and `/app/result_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/queries.json` and writes `/app/output.json`.

The pipeline supports three query types:

- aggregate: GROUP BY with aggregation functions (SUM, AVG, COUNT, MIN, MAX) and optional HAVING clause.
- window: Window functions (ROW_NUMBER, RANK, RUNNING_TOTAL) computed over partitions with configurable frame semantics.
- join_aggregate: Multi-table JOIN followed by GROUP BY aggregation, with optional filter conditions on the join.

The pipeline produces correct output on the current query configuration but has bugs that cause incorrect results on other query configurations with different data characteristics. Find and fix the bugs so the pipeline handles all valid query configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and function signatures. The fixed pipeline will be tested on a different query configuration than the one at `/app/queries.json`.

Output: `/app/output.json` — JSON object with `metadata` (tables_loaded, table_info, query_count) and `results` (list of query result objects, each with query_index, query_type, row_count, columns, and rows).
