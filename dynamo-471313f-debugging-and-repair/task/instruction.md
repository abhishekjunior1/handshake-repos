A work-stealing scheduler simulator at `/app/pipeline.py` processes a task dependency graph (DAG) through multiple simulated workers with work-stealing load balancing. It uses modules `/app/dag_loader.py`, `/app/worker_pool.py`, `/app/task_queue.py`, `/app/scheduler.py`, `/app/sync_primitives.py`, `/app/event_processor.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/schedule.json` and writes `/app/output.json`.

The simulator produces correct output on the current schedule but has bugs that cause incorrect scheduling and timing on other inputs. Find and fix the bugs so the simulator handles all valid DAG schedules correctly.

Do not rewrite from scratch — preserve the existing module structure. Preserve the NUMA-locality steal restriction (adjacent workers only) and the idle-spin backoff convention (exponential backoff before stealing). These are correct optimizations for cache performance and contention reduction in work-stealing runtimes.

Key scheduling conventions for this simulator: work-stealing takes from the TOP of the victim's deque (oldest task — FIFO steal for breadth-first distribution), while the owner pops from the BOTTOM (newest task — LIFO for depth-first execution). Tasks are scheduled by critical-path-length priority (longest remaining path first) to minimize makespan. Dependency resolution uses task finish times to determine when downstream tasks become ready.

The fixed simulator will be tested on a different schedule than the one at `/app/schedule.json`. The test schedule has multiple workers, task dependencies forming a DAG, and varied execution costs that exercise all scheduling paths.

Output: `/app/output.json` — a JSON object with keys: `execution_trace` (list of objects with `task_id`, `worker_id`, `start_time`, `finish_time`, `execution_cost`, `stolen`, `critical_path_length`), `completion_order` (list of task IDs in completion sequence), `scheduling_metrics` (object with `makespan`, `total_tasks`, `total_simulation_ticks`, `critical_path_length`, `speedup`, `efficiency`), `worker_statistics` (per-worker execution data), `steal_statistics` (steal attempt/success counts), and `dependency_timeline` (dependency resolution events).
