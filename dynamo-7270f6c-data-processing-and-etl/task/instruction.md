An ETL pipeline at `/app/data/pipeline.py` processes transaction records through schema validation, transformation, merging, and time-window aggregation. It uses modules `/app/data/schema.py`, `/app/data/transformer.py`, `/app/data/merger.py`, `/app/data/aggregator.py`, and `/app/data/config.py`.

Run it with `cd /app/data && python3 pipeline.py`. It reads `/app/data/source.json` and writes `/app/data/output.json`.

The pipeline produces correct output on the current source data but has bugs that cause incorrect results on other inputs. Find and fix the bugs so the pipeline handles all valid source data correctly.

Do not rewrite from scratch — preserve the existing module structure. The fixed pipeline will be tested on different source data than the one at `/app/data/source.json`.

Output: `/app/data/output.json` — JSON object with aggregated results keyed by time window and category.
