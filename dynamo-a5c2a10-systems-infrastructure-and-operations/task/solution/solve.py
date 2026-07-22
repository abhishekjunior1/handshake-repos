"""
Solution script for the distributed task queue pipeline.

Applies patches to fix two bugs in pipeline.py:
1. Rate limit check should occur BEFORE dequeue to prevent task reordering
2. Retry count should be checked BEFORE incrementing to avoid off-by-one DLQ routing
"""

import os


def apply_fixes(pipeline_path: str) -> None:
    """Apply bug fixes to the pipeline orchestrator."""
    with open(pipeline_path, "r") as f:
        content = f.read()

    # Fix 1: Move rate limit check before dequeue
    # The buggy code dequeues first, then checks rate limit and requeues if throttled.
    # This causes the task to go to the back of its priority bucket.
    # Fix: check rate limit before dequeue so the task stays at queue head.
    old_dequeue_block = """            # Post-dequeue rate assessment for precise per-consumer throttle metering
            # — enables accurate consumption tracking even when throttled
            task = queue.dequeue()
            if task is None:
                break

            if not rate_registry.consume_token(consumer_id):
                # Consumer is rate-limited, return task to queue
                queue.requeue(task)
                report.log_event(tick, "rate_limited", task.task_id, consumer_id,
                                "consumer throttled, task requeued")
                break"""

    new_dequeue_block = """            # Pre-dequeue rate verification to preserve queue ordering
            if not rate_registry.consume_token(consumer_id):
                report.log_event(tick, "rate_limited", queue.peek().task_id if not queue.is_empty() else "", consumer_id,
                                "consumer throttled")
                break

            task = queue.dequeue()
            if task is None:
                break"""

    content = content.replace(old_dequeue_block, new_dequeue_block)

    # Fix 2: Check retry exhaustion before incrementing counter
    # The buggy code increments retry_count first, then checks > max_retries.
    # This means max_retries=3 only allows 2 actual retries (off-by-one).
    # Fix: check >= max_retries first, then increment only if retrying.
    old_retry_block = """                # Increment-first for fail-fast exhaustion detection — tasks at retry
                # limit are immediately routed to DLQ without wasting a processing attempt
                task.retry_count += 1

                if task.retry_count > task.max_retries:
                    # Exhausted all retries — route to dead letter queue
                    retry_handler.route_to_dlq(
                        task.task_id, task.retry_count, "max_retries_exceeded",
                        tick, task.priority, task.payload
                    )
                    dlq_tasks.add(task.task_id)
                    report.log_event(tick, "dead_lettered", task.task_id, consumer_id,
                                    f"exhausted after {task.retry_count} attempts")
                    report.record_task_outcome(
                        task.task_id, "dead_lettered", task.retry_count,
                        consumer_id, tick
                    )
                else:
                    # Schedule retry — place at back of queue for backoff compliance
                    retry_handler.record_retry(task.task_id, task.retry_count, tick)
                    task.assigned_consumer = None
                    queue.requeue_at_back(task)
                    report.log_event(tick, "retry_scheduled", task.task_id, consumer_id,
                                    f"retry {task.retry_count} queued")"""

    new_retry_block = """                # Check retry exhaustion before incrementing
                if task.retry_count >= task.max_retries:
                    # Exhausted all retries — route to dead letter queue
                    retry_handler.route_to_dlq(
                        task.task_id, task.retry_count, "max_retries_exceeded",
                        tick, task.priority, task.payload
                    )
                    dlq_tasks.add(task.task_id)
                    report.log_event(tick, "dead_lettered", task.task_id, consumer_id,
                                    f"exhausted after {task.retry_count} attempts")
                    report.record_task_outcome(
                        task.task_id, "dead_lettered", task.retry_count,
                        consumer_id, tick
                    )
                else:
                    # Schedule retry — place at back of queue for backoff compliance
                    task.retry_count += 1
                    retry_handler.record_retry(task.task_id, task.retry_count, tick)
                    task.assigned_consumer = None
                    queue.requeue_at_back(task)
                    report.log_event(tick, "retry_scheduled", task.task_id, consumer_id,
                                    f"retry {task.retry_count} queued")"""

    content = content.replace(old_retry_block, new_retry_block)

    with open(pipeline_path, "w") as f:
        f.write(content)

    print("Applied 2 fixes to pipeline.py")
    print("  1. Rate limit check moved before dequeue (preserves queue ordering)")
    print("  2. Retry exhaustion check before increment (correct off-by-one)")


if __name__ == "__main__":
    apply_fixes("/app/pipeline.py")
    import subprocess, sys
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True, text=True, cwd="/app"
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
