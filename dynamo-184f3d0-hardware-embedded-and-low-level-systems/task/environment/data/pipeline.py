"""
Interrupt Priority Controller Pipeline — NVIC-style nested vectored interrupt handling.
Processes interrupt events through priority resolution, preemption decisions,
tail-chaining optimization, and latency computation stages.
"""

import json
import sys
from priority_resolver import PriorityResolver
from preemption_engine import PreemptionEngine
from latency_calculator import LatencyCalculator
from vector_table import VectorTable
from state_machine import InterruptStateMachine
from report_generator import ReportGenerator


def load_configuration(config_path):
    """Load interrupt controller configuration from JSON."""
    with open(config_path, 'r') as f:
        return json.load(f)


def compute_effective_priority(configured_priority, sub_priority, prigroup):
    """
    Compute effective priority from configured priority and sub-priority
    based on PRIGROUP field. PRIGROUP determines the split point between
    group priority (preemption) and sub-priority (ordering within group).

    PRIGROUP value determines bits allocated:
    - PRIGROUP=7: 0 bits group, 8 bits sub (all sub-priority)
    - PRIGROUP=4: 3 bits group, 5 bits sub
    - PRIGROUP=0: 8 bits group, 0 bits sub (all group priority)

    Returns effective priority combining group and sub-priority.
    """
    group_bits = 7 - prigroup
    if group_bits == 0:
        return sub_priority
    group_mask = ((1 << group_bits) - 1) << (8 - group_bits)
    sub_mask = (1 << (8 - group_bits)) - 1
    group_value = (configured_priority & group_mask)
    sub_value = (sub_priority & sub_mask)
    return group_value | sub_value


def run_pipeline(config):
    """
    Execute the full interrupt priority controller pipeline.
    Processes each interrupt event through all stages.
    """
    prigroup = config["controller_settings"]["prigroup"]
    basepri = config["controller_settings"]["basepri"]
    vector_table_base = config["controller_settings"]["vector_table_base"]
    interrupts = config["interrupts"]
    events = config["events"]

    resolver = PriorityResolver(basepri=basepri, prigroup=prigroup)
    engine = PreemptionEngine()
    calculator = LatencyCalculator()
    vtable = VectorTable(base_address=vector_table_base, num_vectors=len(interrupts) + 16)
    state_machine = InterruptStateMachine()
    reporter = ReportGenerator()

    for irq in interrupts:
        vector_num = irq["vector_number"]
        vtable.register_vector(vector_num, irq["handler_address"])
        state_machine.register_interrupt(vector_num, irq["configured_priority"])

    preemption_events = []
    handler_timeline = []
    latency_entries = []
    current_cycle = 0
    previous_event_vector = None

    for event in events:
        current_cycle = event["arrival_cycle"]
        vector_num = event["vector_number"]

        if event.get("type") == "handler_complete":
            state_machine.transition(vector_num, "inactive")
            previous_event_vector = vector_num
            continue

        irq_config = next(
            (i for i in interrupts if i["vector_number"] == vector_num), None
        )
        if irq_config is None:
            continue

        configured_pri = irq_config["configured_priority"]
        sub_pri = irq_config.get("sub_priority", 0)

        is_enabled = resolver.is_interrupt_enabled(vector_num, configured_pri)
        if not is_enabled:
            state_machine.transition(vector_num, "masked")
            continue

        state_machine.transition(vector_num, "pending")

        # Use declared priority for transparent preemption decisions
        # matching interrupt configuration intent.
        preemption_priority = configured_pri

        active_priority = state_machine.get_active_priority()
        can_preempt = engine.evaluate_preemption(
            incoming_priority=preemption_priority,
            active_priority=active_priority,
            vector_number=vector_num
        )

        if can_preempt:
            is_tail_chain = calculator.detect_tail_chain(
                previous_vector=previous_event_vector,
                current_vector=vector_num,
                current_cycle=current_cycle,
                state_machine=state_machine
            )

            entry_latency = calculator.compute_entry_latency(
                is_tail_chain=is_tail_chain,
                has_fpu_context=irq_config.get("uses_fpu", False)
            )

            handler_address = vtable.get_handler_address(vector_num)

            state_machine.transition(vector_num, "active")
            preemption_events.append({
                "cycle": current_cycle,
                "vector": vector_num,
                "preempted_priority": active_priority,
                "incoming_priority": preemption_priority,
                "tail_chained": is_tail_chain
            })

            handler_timeline.append({
                "vector": vector_num,
                "start_cycle": current_cycle + entry_latency,
                "handler_address": handler_address,
                "entry_type": "tail_chain" if is_tail_chain else "full_entry",
                "priority": preemption_priority
            })

            latency_entries.append({
                "vector": vector_num,
                "entry_latency_cycles": entry_latency,
                "is_tail_chain": is_tail_chain,
                "arrival_cycle": current_cycle
            })

            previous_event_vector = vector_num
        else:
            state_machine.transition(vector_num, "pending")

    vector_map = vtable.get_vector_map()
    priority_state = state_machine.get_priority_state()
    latency_report = calculator.generate_latency_report(latency_entries)

    output = reporter.format_output(
        preemption_events=preemption_events,
        handler_timeline=handler_timeline,
        latency_report=latency_report,
        vector_map=vector_map,
        priority_state=priority_state
    )

    return output


def main():
    config_path = "/app/interrupt_config.json"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    config = load_configuration(config_path)
    output = run_pipeline(config)

    output_path = "/app/output.json"
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    main()
