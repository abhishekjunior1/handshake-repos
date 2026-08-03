"""Tests for DMA transfer controller output verification (hidden config 3).

The output under test is the report the submitted pipeline produced when the
harness ran it on hidden config 3 — a configuration the agent never saw.
"""

import os
import stat

from dma_verify import (
    harness_status,
    load_config,
    load_expected,
    load_output,
    run_status,
    strict_diff,
)

CONFIG = 3


class TestPipelineRun3:
    """Tests that the submitted pipeline ran and produced a real graded file."""

    def test_pipeline_completed(self):
        """The submitted pipeline must run to completion on hidden config 3."""
        status = run_status(CONFIG)
        assert status["ok"], status["error"] or status["stderr"]

    def test_output_is_a_regular_file(self):
        """/app/output.json must be a real file, not a symlink to the answer key."""
        path = "/app/output.json"
        st = os.lstat(path)
        assert not stat.S_ISLNK(st.st_mode), f"{path} is a symlink"
        assert stat.S_ISREG(st.st_mode), f"{path} is not a regular file"
        assert os.path.realpath(path) == path, f"{path} resolves elsewhere"

    def test_interpreter_not_tampered_with(self):
        """No sitecustomize/usercustomize may be planted to subvert the runner."""
        hooks = harness_status()["interpreter_hooks"]
        assert hooks == [], f"interpreter hook(s) planted: {hooks}"

    def test_answer_key_was_isolated(self):
        """Grading is refused unless the answer key was unreachable during the run."""
        status = harness_status()
        removed = status["answer_key_removed"]
        sealed = status["tests_dir_sealed"] and status["unprivileged"]
        assert removed == [1, 2, 3] or sealed, (
            "answer key was not isolated while the pipeline ran: "
            f"answer_key_removed={removed}, tests_dir_sealed={status['tests_dir_sealed']}, "
            f"unprivileged={status['unprivileged']}")


class TestFullReport3:
    """Test that the whole report matches the expected report exactly."""

    def test_report_matches_expected_exactly(self):
        """Every field of the report must match expected in value and type."""
        diff = strict_diff(load_output(CONFIG), load_expected(CONFIG))
        assert diff is None, diff


class TestSummary3:
    """Tests for the summary section of the DMA output (config 3)."""

    def test_total_bytes_transferred(self):
        """Verify total bytes transferred matches expected value."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["summary"]["total_bytes_transferred"] == expected["summary"]["total_bytes_transferred"]

    def test_total_transfer_operations(self):
        """Verify total transfer operation count matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["summary"]["total_transfer_operations"] == expected["summary"]["total_transfer_operations"]

    def test_total_preemptions(self):
        """Verify total preemption count matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["summary"]["total_preemptions"] == expected["summary"]["total_preemptions"]

    def test_completed_transfers(self):
        """Verify completed transfer count matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["summary"]["completed_transfers"] == expected["summary"]["completed_transfers"]

    def test_average_burst_size(self):
        """Verify average burst size matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["summary"]["average_burst_size"] == expected["summary"]["average_burst_size"]

    def test_total_cycles_used(self):
        """Verify total cycles used matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["summary"]["total_cycles_used"] == expected["summary"]["total_cycles_used"]


class TestTransfers3:
    """Tests for individual transfer records (config 3)."""

    def test_transfer_count(self):
        """Verify number of transfer records matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert len(output["transfers"]) == len(expected["transfers"])

    def test_burst_sizes(self):
        """Verify burst sizes in each transfer match expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["burst_size"] == exp_t["burst_size"], f"Transfer {i} burst_size mismatch"

    def test_bytes_transferred(self):
        """Verify bytes transferred per cycle match expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["bytes_transferred"] == exp_t["bytes_transferred"], f"Transfer {i} bytes mismatch"

    def test_preemption_flags(self):
        """Verify preemption flags match expected per transfer."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["preempted"] == exp_t["preempted"], f"Transfer {i} preempted mismatch"

    def test_completion_flags(self):
        """Verify completion flags match expected per transfer."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["complete"] == exp_t["complete"], f"Transfer {i} complete mismatch"

    def test_channel_ids(self):
        """Verify channel scheduling order matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["channel_id"] == exp_t["channel_id"], f"Transfer {i} channel_id mismatch"

    def test_source_bus_addresses(self):
        """Verify source bus addresses after address translation match expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["source_bus_addr"] == exp_t["source_bus_addr"], f"Transfer {i} source_bus_addr mismatch"

    def test_dest_bus_addresses(self):
        """Verify destination bus addresses after address translation match expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["dest_bus_addr"] == exp_t["dest_bus_addr"], f"Transfer {i} dest_bus_addr mismatch"

    def test_chain_length(self):
        """Verify descriptor chain length per transfer matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["chain_length"] == exp_t["chain_length"], f"Transfer {i} chain_length mismatch"

    def test_cycle_numbers(self):
        """Verify cycle numbers per transfer record match expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["cycle"] == exp_t["cycle"], f"Transfer {i} cycle mismatch"


class TestChannelStatistics3:
    """Tests for per-channel statistics (config 3)."""

    def test_channel_stats_count(self):
        """Verify number of channel statistics entries."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert len(output["channel_statistics"]) == len(expected["channel_statistics"])

    def test_channel_total_bytes(self):
        """Verify per-channel total bytes match expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for out_ch, exp_ch in zip(output["channel_statistics"], expected["channel_statistics"]):
            assert out_ch["total_bytes"] == exp_ch["total_bytes"]

    def test_channel_preemption_count(self):
        """Verify per-channel preemption count matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        for out_ch, exp_ch in zip(output["channel_statistics"], expected["channel_statistics"]):
            assert out_ch["preemption_count"] == exp_ch["preemption_count"]


class TestInterrupts3:
    """Tests for interrupt log entries (config 3)."""

    def test_interrupt_count(self):
        """Verify number of interrupt events matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert len(output["interrupt_log"]) == len(expected["interrupt_log"])


class TestPerformance3:
    """Tests for performance metrics (config 3)."""

    def test_bus_utilization(self):
        """Verify bus utilization metric matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["performance"]["bus_utilization"] == expected["performance"]["bus_utilization"]

    def test_throughput(self):
        """Verify throughput metric matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["performance"]["throughput_bytes_per_cycle"] == expected["performance"]["throughput_bytes_per_cycle"]

    def test_average_latency_cycles(self):
        """Verify average latency cycles metric matches expected."""
        output = load_output(CONFIG)
        expected = load_expected(CONFIG)
        assert output["performance"]["average_latency_cycles"] == expected["performance"]["average_latency_cycles"]


class TestAdvertisedConventions3:
    """Tests for the two conventions instruction.md requires be preserved."""

    def test_bus_addresses_use_negative_offset_translation(self):
        """Bus addresses must sit below physical: bus = physical - bus_offset."""
        output, config = load_output(CONFIG), load_config(CONFIG)
        memory_map = config["memory_map"]
        offset = memory_map["bus_offset"]
        mapped = memory_map.get("iommu_mappings", [])
        channels = {ch["channel_id"]: ch for ch in config["channels"]}
        checked = 0
        for record in output["transfers"]:
            channel = channels[record["channel_id"]]
            for field, source in (("source_bus_addr", "source_address"),
                                  ("dest_bus_addr", "destination_address")):
                physical = channel[source]
                if any(m["physical_start"] <= physical < m["physical_start"] + m["size"]
                       for m in mapped):
                    continue  # IOMMU supplies an alternate translation
                assert record[field] == physical - offset, (
                    f"cycle {record['cycle']} {field}: expected "
                    f"{physical - offset}, got {record[field]}")
                checked += 1
        assert checked > 0, "no transfer exercised address translation"

    def test_interrupt_status_is_write_one_to_clear(self):
        """Status bits are hardware-asserted and never self-clear across events."""
        log = load_output(CONFIG)["interrupt_log"]
        assert log, "no interrupt events recorded"
        previous = 0
        for event in log:
            status = int(event["status_hex"], 16)
            assert status & previous == previous, (
                f"cycle {event['cycle']}: status 0x{status:08x} cleared bits "
                f"set in 0x{previous:08x}; clearing is software's job (W1C)")
            assert status & (1 << event["channel_id"]), (
                f"cycle {event['cycle']}: channel {event['channel_id']} bit not asserted")
            previous = status
