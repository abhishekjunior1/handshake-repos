A task execution pipeline at `/app/runner.py` orchestrates multi-stage builds with dependency resolution, parallel execution, and retry support. It uses modules `/app/resolver.py`, `/app/executor.py`, `/app/condition.py`, `/app/taskfile.py`, and `/app/config.py`.

Run it with `python3 /app/runner.py /app/taskfile.json /app/output.json`. It reads `/app/taskfile.json` and writes `/app/output.json`.

The pipeline produces correct output on the current taskfile but has bugs that cause incorrect behavior on other taskfiles. Find and fix the bugs so the pipeline handles all valid taskfiles correctly.

Do not rewrite from scratch — preserve the existing module structure and output-ordering guarantees. The pipeline's deterministic result ordering and cross-platform value normalization are intentional design choices that must be retained. The fixed pipeline will be tested on different taskfiles than the one at `/app/taskfile.json`.

After fixing, run the pipeline on both evaluation taskfiles and save the outputs:

    python3 /app/runner.py /app/eval_taskfile.json /app/output_eval_1.json
    python3 /app/runner.py /app/eval_taskfile_2.json /app/output_eval_2.json

Outputs: `/app/output_eval_1.json` and `/app/output_eval_2.json` — each a JSON object with "success" boolean, "tasks_executed" list, and "results" object containing per-task execution details.
