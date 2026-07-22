An event processing pipeline at `/app/process.py` aggregates events from `/app/events.json` into time-windowed summaries at `/app/summary.json`. It uses modules `/app/config.py`, `/app/parser.py`, and `/app/aggregator.py`.

Run it with `python3 /app/process.py`. Configuration is at `/app/config.json`.

The pipeline produces correct output on the current event set but has bugs that cause incorrect results on other inputs. Find and fix the bugs so the pipeline handles all valid event data correctly.

Do not rewrite from scratch — preserve the existing module structure. The fixed pipeline will be tested on different events than those at `/app/events.json`.

Output: `/app/summary.json` — JSON object keyed by category, each value an array of window objects with `window`, `count`, `total_score`, and `max_score` fields.
