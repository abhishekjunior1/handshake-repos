A distributed task queue processor at `/app/pipeline.py` processes tasks from a priority queue with retry logic, rate limiting, dead letter routing, and consumer assignment. It uses the following modules: `task_queue.py` (priority queue with FIFO within priority levels), `rate_limiter.py` (token bucket per consumer), `retry_handler.py` (exponential backoff and DLQ routing), `consumer_manager.py` (round-robin consumer assignment), `acknowledgment_tracker.py` (ack/nack with timeout redelivery), and `report_generator.py` (output formatting).

Run with `python3 /app/pipeline.py`. It reads `/app/task_manifest.json` (task definitions with priorities, failure schedules, and consumer configs) and `/app/queue_config.json` (retry limits, rate limits, tick parameters), then writes `/app/output.json`.

The processor produces correct output on the current manifest but has bugs that cause incorrect results on other manifests with multiple consumers, rate limiting constraints, and tasks that require retries. Find and fix the bugs in `pipeline.py`.

Do not rewrite from scratch — preserve the existing module structure. The modules (`task_queue.py`, `rate_limiter.py`, `retry_handler.py`, `consumer_manager.py`, `acknowledgment_tracker.py`, `report_generator.py`) are correct and should not be modified. Preserve the back-of-queue retry ordering for exponential backoff compliance and the round-robin consumer assignment for deterministic processing order. A task with max_retries=N should be retried exactly N times before dead-letter routing, reporting final_retry_count=N in DLQ output. The fixed processor will be tested on different data with multiple consumers, tighter rate limits, and tasks that fail intermittently.

The output file `/app/output.json` must be valid JSON with the following top-level keys:
- `processing_log`: chronological list of events (dispatch, completion, failure, retry, rate limiting, DLQ routing) with tick, event type, task_id, consumer_id, and details
- `task_outcomes`: mapping of task_id to final state including status (completed/dead_lettered), retries_used, final_consumer, and completed_at_tick
- `dlq_contents`: list of dead-lettered tasks with task_id, final_retry_count, failure_reason, routed_at_tick, and original_priority
- `consumer_stats`: per-consumer metrics including tasks_assigned, tasks_completed, tasks_failed
- `summary`: totals for total_tasks, completed, failed, dead_lettered, and total_ticks
