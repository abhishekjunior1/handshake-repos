A task execution pipeline at `/app/runner.py` orchestrates multi-stage builds with dependency resolution, parallel execution, and retry support. It uses modules `/app/resolver.py`, `/app/executor.py`, `/app/condition.py`, `/app/taskfile.py`, and `/app/config.py`.

Run it with `python3 /app/runner.py /app/taskfile.json /app/output.json`. It reads `/app/taskfile.json` and writes `/app/output.json`.

The pipeline produces correct output on the current taskfile but has bugs that cause incorrect behavior on other taskfiles. Find and fix the bugs so the pipeline handles all valid taskfiles correctly.

Do not rewrite from scratch — preserve the existing module structure and output-ordering guarantees. The pipeline's deterministic result ordering and cross-platform value normalization are intentional design choices that must be retained. The fixed pipeline will be tested on a different taskfile than the one at `/app/taskfile.json`.

Output: `/app/output.json` — JSON with "success" boolean, "tasks_executed" list, and "results" object containing per-task execution details.
