A CDC (Change Data Capture) ETL pipeline at `/app/pipeline.py` processes change event streams from source tables, applying schema evolution, deduplication, merge semantics, and SCD Type-2 history tracking to produce a consolidated data warehouse snapshot. It uses modules `/app/event_parser.py`, `/app/dedup_engine.py`, `/app/schema_evolver.py`, `/app/merge_processor.py`, `/app/scd_tracker.py`, and `/app/output_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/events.json` and writes `/app/output.json`.

The pipeline produces correct output on the current event stream but has bugs that cause incorrect results on other event streams. Find and fix the bugs so the pipeline handles all valid CDC event streams correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the last-writer-wins deduplication semantics (keeping the most recent event per key within the deduplication window for eventual consistency) and the retroactive NULL-column backfill for schema evolution (ensuring consistent column sets across all warehouse snapshot rows). The fixed pipeline will be tested on different event streams than the one at `/app/events.json`.

Output: `/app/output.json` — a JSON object with three sections: `warehouse_snapshot` containing the merged rows with `row_count`, `active_count`, and `deleted_count`; `scd_history` containing versioned entity records with `effective_from`, `effective_to`, and `is_current` fields tracking temporal validity; and `pipeline_metrics` containing `deduplication`, `schema_evolution`, and `merge_operations` statistics.
