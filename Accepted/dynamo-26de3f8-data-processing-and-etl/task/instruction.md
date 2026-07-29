A streaming event processing pipeline at `/app/pipeline.py` deduplicates events, assigns them to tumbling time windows, and computes per-key aggregations with exponential decay. It uses modules `/app/event_loader.py`, `/app/window_assigner.py`, `/app/deduplicator.py`, `/app/aggregator.py`, `/app/normalizer.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/events.json` and writes `/app/output.json`.

The pipeline produces correct output on the current event stream but has bugs that cause incorrect results on other streams. Find and fix the bugs so the pipeline handles all valid event data correctly.

Do not rewrite from scratch — preserve the existing module structure and processing logic. The fixed pipeline will be tested on a different event stream than the one at `/app/events.json`.

Output: `/app/output.json` — a JSON object containing per-window aggregation results with key-level statistics, running sums with decay, and deduplication summary.
