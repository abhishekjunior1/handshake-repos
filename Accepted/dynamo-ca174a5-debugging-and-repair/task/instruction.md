A DAG-based pipeline orchestrator at `/app/pipeline.py` executes data processing stages with dependency tracking, state propagation, and retry support. It uses modules `/app/dependencies.py`, `/app/executor.py`, `/app/state.py`, and `/app/scheduler.py`.

Run it with `python3 /app/pipeline.py`. It reads a DAG definition from `/app/dag.json` and writes `/app/execution_log.json`.

The orchestrator works correctly on the current DAG but has bugs that cause incorrect execution on other DAG configurations. Find and fix the bugs so the orchestrator handles all valid DAGs correctly, including those with parallel branches, validation failures, and retry scenarios.

Do not rewrite from scratch — preserve the existing module structure. The fixed orchestrator will be tested on a different DAG than the one at `/app/dag.json`.

Output: `/app/execution_log.json` — JSON array of stage execution records, each with `stage_name`, `execution_order`, `status`, `output_state`, and `attempts`.
