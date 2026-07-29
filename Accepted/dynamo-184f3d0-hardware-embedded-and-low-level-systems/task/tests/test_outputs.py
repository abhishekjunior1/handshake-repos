"""
Verification tests for the Interrupt Priority Controller Pipeline.

Compares pipeline output against expected results on hidden configuration
to verify correct implementation of NVIC priority resolution, preemption,
BASEPRI masking, and tail-chain optimization.
"""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_json(path):
    """Load JSON from file path."""
    with open(path, 'r') as f:
        return json.load(f)


class TestPreemptionEvents:
    """Tests for preemption event correctness."""

    def test_preemption_event_count(self):
        """Verify the correct number of preemption events occurred."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert len(output["preemption_events"]) == len(expected["preemption_events"])

    def test_preemption_event_vectors(self):
        """Verify which vectors triggered preemption events."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_vectors = [e["vector"] for e in output["preemption_events"]]
        expected_vectors = [e["vector"] for e in expected["preemption_events"]]
        assert actual_vectors == expected_vectors

    def test_preemption_priorities(self):
        """Verify effective priorities used in preemption decisions."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["preemption_events"], expected["preemption_events"]):
            assert actual["incoming_priority"] == exp["incoming_priority"]
            assert actual["preempted_priority"] == exp["preempted_priority"]

    def test_preemption_cycles(self):
        """Verify cycle timing of preemption events."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["preemption_events"], expected["preemption_events"]):
            assert actual["cycle"] == exp["cycle"]

    def test_tail_chain_flags(self):
        """Verify tail-chain detection in preemption events."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["preemption_events"], expected["preemption_events"]):
            assert actual["tail_chained"] == exp["tail_chained"]


class TestHandlerTimeline:
    """Tests for handler execution timeline."""

    def test_handler_count(self):
        """Verify the correct number of handlers executed."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert len(output["handler_timeline"]) == len(expected["handler_timeline"])

    def test_handler_vectors(self):
        """Verify which vectors had handlers executed."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_vectors = [h["vector"] for h in output["handler_timeline"]]
        expected_vectors = [h["vector"] for h in expected["handler_timeline"]]
        assert actual_vectors == expected_vectors

    def test_handler_start_cycles(self):
        """Verify handler start cycle timing including entry latency."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["handler_timeline"], expected["handler_timeline"]):
            assert actual["start_cycle"] == exp["start_cycle"]

    def test_handler_entry_types(self):
        """Verify entry type classification (full_entry vs tail_chain)."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["handler_timeline"], expected["handler_timeline"]):
            assert actual["entry_type"] == exp["entry_type"]

    def test_handler_priorities(self):
        """Verify effective priority values reported in timeline."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["handler_timeline"], expected["handler_timeline"]):
            assert actual["priority"] == exp["priority"]

    def test_handler_addresses(self):
        """Verify handler addresses from vector table."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["handler_timeline"], expected["handler_timeline"]):
            assert actual["handler_address"] == exp["handler_address"]


class TestLatencyReport:
    """Tests for latency computation correctness."""

    def test_total_interrupts_processed(self):
        """Verify total interrupt count in latency report."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["latency_report"]["total_interrupts_processed"] == expected["latency_report"]["total_interrupts_processed"]

    def test_entry_type_counts(self):
        """Verify full entry and tail-chain counts."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["latency_report"]["full_entry_count"] == expected["latency_report"]["full_entry_count"]
        assert output["latency_report"]["tail_chain_count"] == expected["latency_report"]["tail_chain_count"]

    def test_average_entry_latency(self):
        """Verify average entry latency computation."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert abs(output["latency_report"]["average_entry_latency"] - expected["latency_report"]["average_entry_latency"]) < 0.01

    def test_total_entry_cycles(self):
        """Verify total entry cycles accumulation."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["latency_report"]["total_entry_cycles"] == expected["latency_report"]["total_entry_cycles"]

    def test_min_max_latency(self):
        """Verify min and max entry latency values."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["latency_report"]["min_entry_latency"] == expected["latency_report"]["min_entry_latency"]
        assert output["latency_report"]["max_entry_latency"] == expected["latency_report"]["max_entry_latency"]

    def test_per_entry_latencies(self):
        """Verify per-interrupt entry latency values."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for actual, exp in zip(output["latency_report"]["entries"], expected["latency_report"]["entries"]):
            assert actual["entry_latency_cycles"] == exp["entry_latency_cycles"]
            assert actual["is_tail_chain"] == exp["is_tail_chain"]


class TestVectorMap:
    """Tests for vector table mapping."""

    def test_vector_map_entries(self):
        """Verify vector table entries and alignment."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert set(output["vector_map"].keys()) == set(expected["vector_map"].keys())
        for vec_num in expected["vector_map"]:
            assert output["vector_map"][vec_num]["entry_alignment_bytes"] == expected["vector_map"][vec_num]["entry_alignment_bytes"]
            assert output["vector_map"][vec_num]["handler_address"] == expected["vector_map"][vec_num]["handler_address"]
            assert output["vector_map"][vec_num]["table_offset"] == expected["vector_map"][vec_num]["table_offset"]


class TestPriorityState:
    """Tests for final interrupt priority state."""

    def test_interrupt_states(self):
        """Verify final state of all registered interrupts."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for vec_num in expected["priority_state"]:
            assert output["priority_state"][vec_num]["state"] == expected["priority_state"][vec_num]["state"], \
                f"Vector {vec_num}: expected state '{expected['priority_state'][vec_num]['state']}', got '{output['priority_state'][vec_num]['state']}'"

    def test_active_handlers(self):
        """Verify which handlers are active and their nesting depth."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        for vec_num in expected["priority_state"]:
            assert output["priority_state"][vec_num]["is_active"] == expected["priority_state"][vec_num]["is_active"]
            assert output["priority_state"][vec_num]["nesting_depth"] == expected["priority_state"][vec_num]["nesting_depth"]

    def test_nmi_hardfault_not_masked(self):
        """Verify NMI and HardFault are never in masked state (bypass BASEPRI)."""
        output = load_json(OUTPUT_PATH)
        if "2" in output["priority_state"]:
            assert output["priority_state"]["2"]["state"] != "masked", \
                "NMI (vector 2) must not be masked by BASEPRI"
        if "3" in output["priority_state"]:
            assert output["priority_state"]["3"]["state"] != "masked", \
                "HardFault (vector 3) must not be masked by BASEPRI"


class TestSummary:
    """Tests for summary metrics."""

    def test_summary_preemptions(self):
        """Verify total preemption count in summary."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["summary"]["total_preemptions"] == expected["summary"]["total_preemptions"]

    def test_summary_handlers(self):
        """Verify total handlers executed in summary."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["summary"]["total_handlers_executed"] == expected["summary"]["total_handlers_executed"]

    def test_summary_tail_chains(self):
        """Verify tail-chain optimization count in summary."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["summary"]["tail_chain_optimizations"] == expected["summary"]["tail_chain_optimizations"]

    def test_summary_latency(self):
        """Verify total and average latency in summary."""
        output = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert output["summary"]["total_latency_cycles"] == expected["summary"]["total_latency_cycles"]
        assert abs(output["summary"]["average_entry_latency"] - expected["summary"]["average_entry_latency"]) < 0.01
