"""Tests for DMA transfer controller output verification (hidden config 1)."""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


def load_output():
    """Load pipeline output from /app/output.json."""
    with open("/app/output.json") as f:
        return json.load(f)


def load_expected():
    """Load expected output for hidden config 1."""
    with open(os.path.join(TESTS_DIR, "expected_output_1.json")) as f:
        return json.load(f)


class TestSummary:
    """Tests for the summary section of the DMA output."""

    def test_total_bytes_transferred(self):
        """Verify total bytes transferred matches expected value."""
        output = load_output()
        expected = load_expected()
        assert output["summary"]["total_bytes_transferred"] == expected["summary"]["total_bytes_transferred"]

    def test_total_transfer_operations(self):
        """Verify total transfer operation count matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["summary"]["total_transfer_operations"] == expected["summary"]["total_transfer_operations"]

    def test_total_preemptions(self):
        """Verify total preemption count matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["summary"]["total_preemptions"] == expected["summary"]["total_preemptions"]

    def test_completed_transfers(self):
        """Verify completed transfer count matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["summary"]["completed_transfers"] == expected["summary"]["completed_transfers"]

    def test_average_burst_size(self):
        """Verify average burst size matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["summary"]["average_burst_size"] == expected["summary"]["average_burst_size"]

    def test_total_cycles_used(self):
        """Verify total cycles used matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["summary"]["total_cycles_used"] == expected["summary"]["total_cycles_used"]


class TestTransfers:
    """Tests for individual transfer records."""

    def test_transfer_count(self):
        """Verify number of transfer records matches expected."""
        output = load_output()
        expected = load_expected()
        assert len(output["transfers"]) == len(expected["transfers"])

    def test_burst_sizes(self):
        """Verify burst sizes in each transfer match expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["burst_size"] == exp_t["burst_size"], f"Transfer {i} burst_size mismatch"

    def test_bytes_transferred(self):
        """Verify bytes transferred per cycle match expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["bytes_transferred"] == exp_t["bytes_transferred"], f"Transfer {i} bytes mismatch"

    def test_preemption_flags(self):
        """Verify preemption flags match expected per transfer."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["preempted"] == exp_t["preempted"], f"Transfer {i} preempted mismatch"

    def test_completion_flags(self):
        """Verify completion flags match expected per transfer."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["complete"] == exp_t["complete"], f"Transfer {i} complete mismatch"

    def test_channel_ids(self):
        """Verify channel scheduling order matches expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["channel_id"] == exp_t["channel_id"], f"Transfer {i} channel_id mismatch"

    def test_source_bus_addresses(self):
        """Verify source bus addresses after address translation match expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["source_bus_addr"] == exp_t["source_bus_addr"], f"Transfer {i} source_bus_addr mismatch"

    def test_dest_bus_addresses(self):
        """Verify destination bus addresses after address translation match expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["dest_bus_addr"] == exp_t["dest_bus_addr"], f"Transfer {i} dest_bus_addr mismatch"

    def test_chain_length(self):
        """Verify descriptor chain length per transfer matches expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["chain_length"] == exp_t["chain_length"], f"Transfer {i} chain_length mismatch"

    def test_cycle_numbers(self):
        """Verify cycle numbers per transfer record match expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["cycle"] == exp_t["cycle"], f"Transfer {i} cycle mismatch"

    def test_total_transfers_per_record(self):
        """Verify total_transfers count per record matches expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_t, exp_t) in enumerate(zip(output["transfers"], expected["transfers"])):
            assert out_t["total_transfers"] == exp_t["total_transfers"], f"Transfer {i} total_transfers mismatch"


class TestChannelStatistics:
    """Tests for per-channel statistics."""

    def test_channel_stats_count(self):
        """Verify number of channel statistics entries."""
        output = load_output()
        expected = load_expected()
        assert len(output["channel_statistics"]) == len(expected["channel_statistics"])

    def test_channel_total_bytes(self):
        """Verify per-channel total bytes match expected."""
        output = load_output()
        expected = load_expected()
        for out_ch, exp_ch in zip(output["channel_statistics"], expected["channel_statistics"]):
            assert out_ch["total_bytes"] == exp_ch["total_bytes"], f"Channel {out_ch['channel_id']} bytes mismatch"

    def test_channel_preemption_count(self):
        """Verify per-channel preemption count matches expected."""
        output = load_output()
        expected = load_expected()
        for out_ch, exp_ch in zip(output["channel_statistics"], expected["channel_statistics"]):
            assert out_ch["preemption_count"] == exp_ch["preemption_count"]


class TestInterrupts:
    """Tests for interrupt log entries."""

    def test_interrupt_count(self):
        """Verify number of interrupt events matches expected."""
        output = load_output()
        expected = load_expected()
        assert len(output["interrupt_log"]) == len(expected["interrupt_log"])

    def test_interrupt_status_bits(self):
        """Verify interrupt status register values match expected."""
        output = load_output()
        expected = load_expected()
        for i, (out_irq, exp_irq) in enumerate(zip(output["interrupt_log"], expected["interrupt_log"])):
            assert out_irq["status_hex"] == exp_irq["status_hex"], f"IRQ {i} status mismatch"


class TestPerformance:
    """Tests for performance metrics."""

    def test_bus_utilization(self):
        """Verify bus utilization metric matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["performance"]["bus_utilization"] == expected["performance"]["bus_utilization"]

    def test_throughput(self):
        """Verify throughput metric matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["performance"]["throughput_bytes_per_cycle"] == expected["performance"]["throughput_bytes_per_cycle"]

    def test_average_latency_cycles(self):
        """Verify average latency cycles metric matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["performance"]["average_latency_cycles"] == expected["performance"]["average_latency_cycles"]
