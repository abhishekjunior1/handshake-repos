"""
Test suite for SPI/I2C Peripheral Initialization Pipeline.
Validates the pipeline output against expected results on hidden input data.
"""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


@pytest.fixture
def output():
    """Load the pipeline output."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Load the expected output."""
    with open(EXPECTED_PATH, "r") as f:
        return json.load(f)


class TestInitializationSummary:
    """Tests for top-level initialization summary."""

    def test_total_init_time(self, output, expected):
        """Verify total initialization time accounts for PLL lock and power sequencing."""
        assert output["initialization_summary"]["total_init_time_us"] == expected["initialization_summary"]["total_init_time_us"]

    def test_all_peripherals_initialized(self, output, expected):
        """Verify overall initialization success status reflects clock stability."""
        assert output["initialization_summary"]["all_peripherals_initialized"] == expected["initialization_summary"]["all_peripherals_initialized"]

    def test_devices_programmed(self, output, expected):
        """Verify register programming count depends on clock stability."""
        assert output["initialization_summary"]["devices_programmed"] == expected["initialization_summary"]["devices_programmed"]

    def test_devices_lost(self, output, expected):
        """Verify lost register count when programming before PLL lock."""
        assert output["initialization_summary"]["devices_lost"] == expected["initialization_summary"]["devices_lost"]

    def test_devices_enumerated(self, output, expected):
        """Verify device enumeration count."""
        assert output["initialization_summary"]["devices_enumerated"] == expected["initialization_summary"]["devices_enumerated"]

    def test_power_domains_enabled(self, output, expected):
        """Verify power domain count."""
        assert output["initialization_summary"]["power_domains_enabled"] == expected["initialization_summary"]["power_domains_enabled"]


class TestClockConfiguration:
    """Tests for clock tree configuration."""

    def test_system_clock(self, output, expected):
        """Verify system clock derived from PLL configuration."""
        assert output["clock_configuration"]["system_clock_mhz"] == expected["clock_configuration"]["system_clock_mhz"]

    def test_bus_clock(self, output, expected):
        """Verify bus clock is system clock divided by bus_divider."""
        assert output["clock_configuration"]["bus_clock_mhz"] == expected["clock_configuration"]["bus_clock_mhz"]

    def test_pll_lock_time(self, output, expected):
        """Verify PLL lock time computation."""
        assert output["clock_configuration"]["pll_lock_time_us"] == expected["clock_configuration"]["pll_lock_time_us"]

    def test_pll_enabled(self, output, expected):
        """Verify PLL enabled status."""
        assert output["clock_configuration"]["pll_enabled"] == expected["clock_configuration"]["pll_enabled"]

    def test_clock_stable_at_t0(self, output, expected):
        """Verify clock stability flag when PLL is configured."""
        assert output["clock_configuration"]["clock_stable_at_t0"] == expected["clock_configuration"]["clock_stable_at_t0"]


class TestPowerSequencing:
    """Tests for power domain enable sequencing."""

    def test_enable_sequence_order(self, output, expected):
        """Verify power domains enabled in correct inner-to-outer order."""
        actual_names = [e["domain_name"] for e in output["power_sequencing"]["enable_sequence"]]
        expected_names = [e["domain_name"] for e in expected["power_sequencing"]["enable_sequence"]]
        assert actual_names == expected_names

    def test_total_power_up_time(self, output, expected):
        """Verify cumulative power-up timing."""
        assert output["power_sequencing"]["total_power_up_time_us"] == expected["power_sequencing"]["total_power_up_time_us"]

    def test_sequencing_valid(self, output, expected):
        """Verify power sequencing passes hardware constraints."""
        assert output["power_sequencing"]["sequencing_valid"] == expected["power_sequencing"]["sequencing_valid"]

    def test_domain_count(self, output, expected):
        """Verify all power domains are sequenced."""
        assert output["power_sequencing"]["domain_count"] == expected["power_sequencing"]["domain_count"]


class TestBusTransactions:
    """Tests for bus arbitration and chip select management."""

    def test_cs_sequence_count(self, output, expected):
        """Verify chip select sequence covers all peripherals."""
        assert len(output["bus_transactions"]["cs_sequence"]) == len(expected["bus_transactions"]["cs_sequence"])

    def test_cs_polarity(self, output, expected):
        """Verify correct chip select polarity for all devices."""
        for actual, exp in zip(output["bus_transactions"]["cs_sequence"], expected["bus_transactions"]["cs_sequence"]):
            assert actual["cs_polarity"] == exp["cs_polarity"]
            assert actual["cs_assert"] == exp["cs_assert"]
            assert actual["cs_deassert"] == exp["cs_deassert"]

    def test_deassert_signals(self, output, expected):
        """Verify chip select deassert uses correct polarity logic."""
        assert output["bus_transactions"]["deassert_signals"] == expected["bus_transactions"]["deassert_signals"]

    def test_bus_timing_peripheral_clock(self, output, expected):
        """Verify bus timing derived from correct peripheral clock rate."""
        assert output["bus_transactions"]["timing"]["clock_period_ns"] == expected["bus_transactions"]["timing"]["clock_period_ns"]
        assert output["bus_transactions"]["timing"]["max_freq_mhz"] == expected["bus_transactions"]["timing"]["max_freq_mhz"]


class TestRegisterProgramming:
    """Tests for register write sequence execution."""

    def test_total_registers_programmed(self, output, expected):
        """Verify total registers successfully programmed."""
        assert output["register_programming"]["total_registers_programmed"] == expected["register_programming"]["total_registers_programmed"]

    def test_total_registers_lost(self, output, expected):
        """Verify register writes lost due to clock instability."""
        assert output["register_programming"]["total_registers_lost"] == expected["register_programming"]["total_registers_lost"]

    def test_per_device_results(self, output, expected):
        """Verify per-device programming results match expected."""
        assert output["register_programming"]["per_device_results"] == expected["register_programming"]["per_device_results"]

    def test_all_devices_successful(self, output, expected):
        """Verify overall success flag reflects actual programming outcome."""
        assert output["register_programming"]["all_devices_successful"] == expected["register_programming"]["all_devices_successful"]


class TestDeviceEnumeration:
    """Tests for device discovery on bus."""

    def test_devices_scanned(self, output, expected):
        """Verify all devices on bus were scanned."""
        assert output["device_enumeration"]["total_devices_scanned"] == expected["device_enumeration"]["total_devices_scanned"]

    def test_devices_identified(self, output, expected):
        """Verify device ID matching count."""
        assert output["device_enumeration"]["devices_identified"] == expected["device_enumeration"]["devices_identified"]

    def test_enumeration_complete(self, output, expected):
        """Verify enumeration completion status."""
        assert output["device_enumeration"]["enumeration_complete"] == expected["device_enumeration"]["enumeration_complete"]


class TestDiagnostics:
    """Tests for diagnostic output fields."""

    def test_clock_stable_at_programming(self, output, expected):
        """Verify clock stability diagnostic reflects actual PLL state."""
        assert output["diagnostics"]["clock_stable_at_programming"] == expected["diagnostics"]["clock_stable_at_programming"]

    def test_peripheral_clock_mhz(self, output, expected):
        """Verify peripheral clock rate derived from bus clock chain."""
        assert output["diagnostics"]["peripheral_clock_mhz"] == expected["diagnostics"]["peripheral_clock_mhz"]

    def test_bus_contention(self, output, expected):
        """Verify bus contention detection for multi-device configuration."""
        assert output["diagnostics"]["bus_contention_detected"] == expected["diagnostics"]["bus_contention_detected"]
