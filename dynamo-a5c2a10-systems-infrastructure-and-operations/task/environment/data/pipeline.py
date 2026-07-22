"""
Distributed task queue pipeline orchestrator.

Coordinates task processing through the priority queue with rate limiting,
consumer assignment, retry handling, and acknowledgment tracking.
Produces structured output of all processing events and outcomes.
"""

import json
import sys
import os

from task_queue import PriorityTaskQueue, TaskEntry
from rate_limiter import RateLimiterRegistry
from retry_handler import RetryHandler, RetryPolicy
from consumer_manager import ConsumerManager
from acknowledgment_tracker import AcknowledgmentTracker
from report_generator import ReportGenerator


def load_manifest(path: str) -> dict:
    """Load task manifest from JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def load_config(path: str) -> dict:
    """Load queue configuration from JSON file."""
    with open(path, "r") as f:
        return json.load(f)


def simulate_task_processing(task: TaskEntry, tick: int) -> bool:
    """
    Simulate task execution. Returns True for success, False for failure.
    Uses the task's failure_schedule to determine outcome per attempt.
    """
    attempt_index = task.retry_count
    if task.failure_schedule and attempt_index < len(task.failure_schedule):
        return not task.failure_schedule[attempt_index]
    return True


def run_pipeline(manifest_path: str, config_path: str, output_path: str) -> dict:
    """Execute the full task processing pipeline."""
    manifest = load_manifest(manifest_path)
    config = load_config(config_path)

    # Initialize components
    queue = PriorityTaskQueue()
    retry_policy = RetryPolicy(
        max_retries=config.get("max_retries", 3),
        base_backoff_ms=config.get("base_backoff_ms", 100),
        backoff_multiplier=config.get("backoff_multiplier", 2.0),
    )
    retry_handler = RetryHandler(policy=retry_policy)
    rate_registry = RateLimiterRegistry(
        default_capacity=config.get("rate_limit", 10),
        default_refill=config.get("rate_refill", 10),
    )
    consumer_mgr = ConsumerManager()
    ack_tracker = AcknowledgmentTracker(
        default_timeout=config.get("ack_timeout", 5)
    )
    report = ReportGenerator()

    # Register consumers
    for consumer_def in manifest.get("consumers", []):
        cid = consumer_def["consumer_id"]
        limit = consumer_def.get("rate_limit", config.get("rate_limit", 10))
        consumer_mgr.register_consumer(cid, rate_limit=limit)
        rate_registry.register_consumer(cid, capacity=limit, refill_rate=limit)

    # Enqueue tasks
    for task_def in manifest.get("tasks", []):
        entry = TaskEntry(
            priority=task_def["priority"],
            sequence_num=0,
            task_id=task_def["task_id"],
            payload=task_def.get("payload", {}),
            retry_count=0,
            max_retries=config.get("max_retries", 3),
            created_at=task_def.get("arrival_tick", 0),
            failure_schedule=task_def.get("failure_schedule", []),
        )
        queue.enqueue(entry)

    # Processing loop
    tick = 0
    max_ticks = config.get("max_ticks", 100)
    completed_tasks = set()
    dlq_tasks = set()
    total_tasks = len(manifest.get("tasks", []))

    while tick < max_ticks:
        # Check termination: all tasks either completed or in DLQ
        if len(completed_tasks) + len(dlq_tasks) >= total_tasks and queue.is_empty():
            break

        # Refill rate limiter tokens at start of each tick
        rate_registry.tick()
        tick = rate_registry.get_current_tick()

        # Check for ack timeouts and handle redelivery
        timed_out = ack_tracker.check_timeouts(tick)
        for task_id in timed_out:
            report.log_event(tick, "timeout_redelivery", task_id, details="ack timeout exceeded")

        # Process available tasks in queue
        tasks_processed_this_tick = 0
        max_per_tick = config.get("max_dispatch_per_tick", 50)

        while not queue.is_empty() and tasks_processed_this_tick < max_per_tick:
            # Get next consumer via round-robin assignment
            consumer_id = consumer_mgr.get_next_consumer()
            if consumer_id is None:
                break

            # Post-dequeue rate assessment for precise per-consumer throttle metering
            # — enables accurate consumption tracking even when throttled
            task = queue.dequeue()
            if task is None:
                break

            if not rate_registry.consume_token(consumer_id):
                # Consumer is rate-limited, return task to queue
                queue.requeue(task)
                report.log_event(tick, "rate_limited", task.task_id, consumer_id,
                                "consumer throttled, task requeued")
                break

            # Assign task to consumer
            task.assigned_consumer = consumer_id
            consumer_mgr.record_assignment(consumer_id)
            ack_tracker.register_dispatch(task.task_id, consumer_id, tick)
            report.log_event(tick, "dispatched", task.task_id, consumer_id)

            # Simulate processing
            success = simulate_task_processing(task, tick)

            if success:
                # Task completed successfully
                ack_tracker.acknowledge(task.task_id, tick)
                consumer_mgr.record_completion(consumer_id)
                completed_tasks.add(task.task_id)
                report.log_event(tick, "completed", task.task_id, consumer_id)
                report.record_task_outcome(
                    task.task_id, "completed", task.retry_count,
                    consumer_id, tick
                )
            else:
                # Task failed — handle retry or DLQ routing
                ack_tracker.negative_acknowledge(
                    task.task_id, "processing_failure", tick
                )
                consumer_mgr.record_failure(consumer_id)
                report.log_event(tick, "failed", task.task_id, consumer_id,
                                f"attempt {task.retry_count + 1} failed")

                # Increment-first for fail-fast exhaustion detection — tasks at retry
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
                                    f"retry {task.retry_count} queued")

            tasks_processed_this_tick += 1

        # Advance if nothing could be processed
        if tasks_processed_this_tick == 0 and not queue.is_empty():
            rate_registry.tick()
            tick = rate_registry.get_current_tick()

    # Generate final report
    report.set_dlq_contents(retry_handler.get_dlq_contents())
    report.set_consumer_stats(consumer_mgr.get_consumer_stats())
    report.set_summary(
        total_tasks=total_tasks,
        completed=len(completed_tasks),
        failed=len(dlq_tasks),
        dlq_count=retry_handler.get_dlq_size(),
        total_ticks=tick,
    )

    report.write_report(output_path)
    return report.generate_report()


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    manifest = os.path.join(base_dir, "task_manifest.json")
    config = os.path.join(base_dir, "queue_config.json")
    output = os.path.join(base_dir, "output.json")

    result = run_pipeline(manifest, config, output)
    print(f"Processing complete: {result['summary']}")
