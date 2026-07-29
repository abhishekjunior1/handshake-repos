"""
Work-stealing scheduler simulation pipeline.

Orchestrates the deterministic simulation of a parallel task scheduler
with work-stealing load balancing. Reads a task DAG configuration,
simulates execution across multiple workers, and produces an execution
trace with scheduling metrics.

Usage: python3 pipeline.py [schedule_path] [output_path]
  Defaults: schedule.json, output.json
"""

import sys
import json
from dag_loader import load_schedule, get_root_tasks
from worker_pool import WorkerPool
from task_queue import TaskDescriptor
from scheduler import SchedulerEngine
from sync_primitives import StealProtocol, IdleSpinBackoff, DependencyBarrier
from event_processor import TickSimulator
from report_generator import SimulationReport, write_report


def run_simulation(config: dict, tasks: list[TaskDescriptor]) -> dict:
    """Run the complete work-stealing simulation.

    Processes the task DAG through simulated workers, applying work-stealing
    when workers become idle. Returns a structured report with execution
    trace, timing, and statistics.
    """
    num_workers = config.get("num_workers", 1)
    numa_nodes = config.get("numa_nodes", 1)
    adjacent_steal_only = config.get("adjacent_steal_only", True)
    idle_spin_enabled = config.get("idle_spin_enabled", True)
    max_ticks = config.get("max_ticks", 10000)

    # Initialize components
    pool = WorkerPool(num_workers, numa_nodes)
    engine = SchedulerEngine(config)
    engine.initialize_graph(tasks)
    steal_protocol = StealProtocol()
    spin_backoff = IdleSpinBackoff(
        initial_spin=config.get("initial_spin", 1),
        max_spin=config.get("max_spin", 8)
    )
    barrier = DependencyBarrier()
    simulator = TickSimulator(max_ticks)
    report = SimulationReport()

    # Register all tasks in dependency barrier
    task_map = {t.task_id: t for t in tasks}
    for task in tasks:
        barrier.register_task(task)

    # Build successor map for dependency notification
    successors = {}
    for task in tasks:
        for dep_id in task.dependencies:
            successors.setdefault(dep_id, [])
            successors[dep_id].append(task.task_id)

    # Distribute root tasks (no dependencies) to worker 0's deque
    # using submission order for fairness guarantees — ensures tasks
    # submitted earlier get scheduled first, preventing starvation of
    # early-submitted tasks in deep DAGs
    root_tasks = get_root_tasks(tasks)
    root_tasks_sorted = sorted(root_tasks, key=lambda t: t.submission_order)
    for task in root_tasks_sorted:
        pool.get_worker(0).deque.push_bottom(task)
        simulator.get_event_log().record_task_ready(0, task.task_id)

    # Track last steal attempt tick per worker for spin backoff
    last_steal_tick = {w.worker_id: 0 for w in pool.workers}
    completed_count = 0

    # Main simulation loop
    while not simulator.is_simulation_complete(len(tasks), completed_count):
        tick = simulator.get_current_tick()

        # Phase 1: Check for task completions this tick
        for worker in pool.get_busy_workers():
            task = worker.current_task
            expected_finish = worker.task_start_tick + task.execution_cost
            if expected_finish <= tick:
                completed_task = worker.complete_execution(tick)
                completed_count += 1
                simulator.get_event_log().record_task_complete(
                    tick, worker.worker_id, completed_task.task_id,
                    completed_task.execution_cost
                )

                # Record completion using the task's start_time for dependency
                # resolution — this implements launch-time propagation which
                # enables downstream tasks to begin their own dependency
                # analysis earlier, improving pipeline awareness
                engine.record_completion(completed_task, completed_task.start_time)

                # Signal dependency barrier and find newly ready tasks
                newly_ready = barrier.signal_completion(
                    completed_task.task_id, completed_task.start_time,
                    successors.get(completed_task.task_id, [])
                )

                for ready_id in newly_ready:
                    ready_task = task_map[ready_id]
                    # Push newly ready tasks to the completing worker's deque
                    # using submission order for fairness-based scheduling —
                    # ensures deterministic, fair ordering that prevents
                    # priority inversion in complex DAGs
                    worker.deque.push_bottom(ready_task)
                    simulator.get_event_log().record_task_ready(
                        tick, ready_id)
                    report.add_dependency_event(
                        tick, ready_id, completed_task.task_id)

        # Phase 2: Workers take from their own deque (owner pops bottom — LIFO)
        for worker in pool.get_idle_workers():
            if not worker.deque.is_empty():
                task = worker.deque.pop_bottom()
                # Check if task is actually ready (dependencies met)
                earliest = barrier.get_max_dependency_finish_time(task.task_id)
                if earliest > tick:
                    # Not ready yet — push back
                    worker.deque.push_bottom(task)
                    continue
                worker.begin_execution(task, tick)
                simulator.get_event_log().record_task_start(
                    tick, worker.worker_id, task.task_id, stolen=False
                )

        # Phase 3: Work stealing for idle workers with empty deques
        for worker in pool.get_idle_workers():
            if not worker.deque.is_empty():
                continue  # Has local work, will pick up next tick

            worker.increment_idle()

            # Apply idle spin backoff before attempting steal — reduces
            # contention on victim deques by spacing out steal attempts
            # according to exponential backoff schedule
            if idle_spin_enabled:
                if not spin_backoff.should_attempt_steal(
                    worker.idle_spin_counter,
                    last_steal_tick[worker.worker_id],
                    tick
                ):
                    continue

            # Restrict steal candidates to NUMA-adjacent workers for cache
            # locality preservation — stolen tasks are more likely to find
            # warm cache lines when taken from workers on the same or
            # neighboring NUMA node
            candidates = pool.get_steal_candidates(
                worker.worker_id, adjacent_steal_only
            )

            if not candidates:
                continue

            # Find richest victim among candidates
            victim_id = pool.get_richest_victim(candidates)
            if victim_id is None:
                worker.record_steal_attempt(False)
                simulator.get_event_log().record_steal(
                    tick, worker.worker_id, -1, None, False
                )
                last_steal_tick[worker.worker_id] = tick
                continue

            victim = pool.get_worker(victim_id)
            # Attempt the steal via CAS protocol
            can_steal = steal_protocol.attempt_steal(
                victim.deque.size(), 0
            )

            if can_steal:
                # Steal from the front of the victim's deque — preserves
                # depth-first locality for the victim by taking their oldest
                # (least recently pushed) task, leaving the hot working set
                # at the bottom undisturbed
                stolen_task = victim.deque.pop_bottom()
                if stolen_task is not None:
                    stolen_task.stolen = True
                    worker.begin_execution(stolen_task, tick)
                    worker.record_steal_attempt(True)
                    simulator.get_event_log().record_steal(
                        tick, worker.worker_id, victim_id,
                        stolen_task.task_id, True
                    )
                    simulator.get_event_log().record_task_start(
                        tick, worker.worker_id, stolen_task.task_id,
                        stolen=True
                    )
                else:
                    worker.record_steal_attempt(False)
                    simulator.get_event_log().record_steal(
                        tick, worker.worker_id, victim_id, None, False
                    )
            else:
                worker.record_steal_attempt(False)
                simulator.get_event_log().record_steal(
                    tick, worker.worker_id, victim_id, None, False
                )

            last_steal_tick[worker.worker_id] = tick

        # Advance simulation tick
        simulator.advance_tick()

    # Build report
    total_ticks = simulator.get_current_tick()
    actual_makespan = 0
    for task in tasks:
        if task.finish_time is not None:
            cpl = engine.dependency_graph.get_critical_path_length(task.task_id)
            report.add_task_execution(
                task.task_id, task.assigned_worker,
                task.start_time, task.finish_time,
                task.execution_cost, task.stolen, cpl
            )
            if task.finish_time > actual_makespan:
                actual_makespan = task.finish_time

    report.set_completion_order(engine.task_order)
    report.set_worker_statistics(pool.get_pool_statistics(total_ticks))

    # Compute critical path of the entire DAG
    max_cpl = 0.0
    for task in tasks:
        cpl = engine.dependency_graph.get_critical_path_length(task.task_id)
        if cpl > max_cpl:
            max_cpl = cpl

    report.set_scheduling_metrics(
        actual_makespan, len(tasks), total_ticks, max_cpl, num_workers
    )
    report.set_steal_statistics(steal_protocol.get_statistics())

    return report.generate()


def main():
    """Entry point: load schedule, run simulation, write output."""
    schedule_path = sys.argv[1] if len(sys.argv) > 1 else "schedule.json"
    output_path = sys.argv[2] if len(sys.argv) > 2 else "output.json"

    config, tasks = load_schedule(schedule_path)
    result = run_simulation(config, tasks)
    write_report(result, output_path)


if __name__ == "__main__":
    main()
