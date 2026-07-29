A query execution plan optimizer pipeline at `/app/pipeline.py` generates execution plans for SQL queries. It uses modules `/app/query_parser.py`, `/app/catalog_manager.py`, `/app/cost_estimator.py`, `/app/join_optimizer.py`, `/app/index_advisor.py`, and `/app/plan_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/db_config.json` and writes `/app/output.json`.

The optimizer produces correct plans on the current database configuration but has bugs that cause suboptimal plan selection and incorrect cardinality estimates on other configurations. Find and fix the bugs so the optimizer handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and optimization approach. In particular, preserve the composite index correlation computation using maximum per-column correlation in `cost_estimator.py` (the PostgreSQL convention where the most-ordered column dominates), and preserve the explicit sort-cost merge join evaluation in `join_optimizer.py` (which ensures deterministic plan comparison independent of input access paths). The fixed optimizer will be tested on a different database configuration than the one at `/app/db_config.json`.

Output: `/app/output.json` — JSON with `optimizer_version` string and `plans` array containing per-query objects with `database`, `query`, `plan_summary` (total_estimated_cost, estimated_output_rows, join_strategy, table_access_strategies), `scan_plans`, `join_plan`, `statistics_status`, `index_analysis`, `cost_breakdown`, and `optimization_notes`.
