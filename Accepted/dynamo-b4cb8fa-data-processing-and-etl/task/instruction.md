A tabular data transformation pipeline at `/app/pipeline.py` loads input tables, applies column mappings, joins, pivots, derived column computations, and aggregations. It uses modules `/app/data_loader.py`, `/app/column_mapper.py`, `/app/pivot_ops.py`, `/app/join_ops.py`, `/app/aggregator.py`, and `/app/output_writer.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/transform_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

When pivot encounters multiple rows with the same index and pivot column combination, it should sum their values rather than keeping only one.

Do not rewrite from scratch — preserve the existing module structure and transformation semantics. The fixed pipeline will be tested on a different configuration than the one at `/app/transform_config.json`.

Output: `/app/output.json` — a JSON object with `metadata` (row_count, columns, transformations_applied, source_tables) and `data` (list of transformed row objects with the computed values).
