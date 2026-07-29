"""
Solution for the work-stealing scheduler simulator.

Patches three bugs in pipeline.py:
1. Root task scheduling uses submission_order instead of critical_path_length
2. Work stealing uses pop_bottom (LIFO) instead of steal_top (FIFO steal)
3. Dependency resolution uses start_time instead of finish_time
"""

import subprocess
import sys


def patch_pipeline():
    """Apply patches to pipeline.py and run the simulation."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, 'r') as f:
        content = f.read()

    # Bug 1: Root tasks should be sorted by -critical_path_length (longest path first)
    # not by submission_order. The engine.get_scheduling_priority() returns -CPL.
    content = content.replace(
        "root_tasks_sorted = sorted(root_tasks, key=lambda t: t.submission_order)",
        "root_tasks_sorted = sorted(root_tasks, key=lambda t: engine.get_scheduling_priority(t))"
    )

    # Bug 2: Work stealing should use steal_top() which takes from the TOP
    # of the victim's deque (oldest task = breadth-first distribution),
    # not pop_bottom() which takes from the BOTTOM (newest = LIFO).
    content = content.replace(
        "stolen_task = victim.deque.pop_bottom()",
        "stolen_task = victim.deque.steal_top()"
    )

    # Bug 3: Dependency resolution must use finish_time (when the task actually
    # completed) not start_time (when it began). Downstream tasks cannot start
    # until dependencies FINISH, not when they start.
    content = content.replace(
        "engine.record_completion(completed_task, completed_task.start_time)",
        "engine.record_completion(completed_task, completed_task.finish_time)"
    )
    content = content.replace(
        "completed_task.task_id, completed_task.start_time,\n                    successors.get(completed_task.task_id, [])",
        "completed_task.task_id, completed_task.finish_time,\n                    successors.get(completed_task.task_id, [])"
    )

    with open(pipeline_path, 'w') as f:
        f.write(content)

    # Run the fixed pipeline
    subprocess.run(
        [sys.executable, pipeline_path, "/app/schedule.json", "/app/output.json"],
        cwd="/app",
        check=True
    )


if __name__ == "__main__":
    patch_pipeline()
