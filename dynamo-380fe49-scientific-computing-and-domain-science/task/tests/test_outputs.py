"""
Test suite for thermal-mechanical coupling simulation pipeline.

Verifies that the pipeline produces correct output on a hidden test configuration
by comparing against pre-computed expected values with relative tolerance.
"""

import json
import os
import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
PIPELINE_OUTPUT_PATH = "/app/output.json"

REL_TOL = 1e-4


def load_expected():
    """Load expected output from test fixtures."""
    with open(EXPECTED_OUTPUT_PATH, "r") as f:
        return json.load(f)


def load_actual():
    """Load actual pipeline output."""
    with open(PIPELINE_OUTPUT_PATH, "r") as f:
        return json.load(f)


def rel_close(actual, expected, tol=REL_TOL):
    """Check if two values are within relative tolerance."""
    if abs(expected) < 1e-12:
        return abs(actual) < tol
    return abs(actual - expected) / abs(expected) < tol


class TestThermalMechanicalOutput:
    """Tests verifying correctness of the thermal-mechanical simulation."""

    def test_output_file_exists(self):
        """Verify that the pipeline produced an output file."""
        assert os.path.exists(PIPELINE_OUTPUT_PATH)

    def test_output_schema(self):
        """Verify the output JSON has required top-level keys."""
        actual = load_actual()
        assert "simulation_time_s" in actual
        assert "profiles" in actual
        assert "diagnostics" in actual

    def test_simulation_time(self):
        """Verify simulation ran for the correct total time."""
        actual = load_actual()
        expected = load_expected()
        assert rel_close(actual["simulation_time_s"], expected["simulation_time_s"])

    def test_max_temperature(self):
        """Verify maximum temperature matches expected value."""
        actual = load_actual()
        expected = load_expected()
        assert rel_close(
            actual["diagnostics"]["max_temperature_K"],
            expected["diagnostics"]["max_temperature_K"]
        ), (
            f"Max temperature: got {actual['diagnostics']['max_temperature_K']:.4f}, "
            f"expected {expected['diagnostics']['max_temperature_K']:.4f}"
        )

    def test_max_stress(self):
        """Verify maximum thermal stress matches expected value."""
        actual = load_actual()
        expected = load_expected()
        assert rel_close(
            actual["diagnostics"]["max_stress_Pa"],
            expected["diagnostics"]["max_stress_Pa"]
        ), (
            f"Max stress: got {actual['diagnostics']['max_stress_Pa']:.4e}, "
            f"expected {expected['diagnostics']['max_stress_Pa']:.4e}"
        )

    def test_max_displacement(self):
        """Verify maximum displacement matches expected value."""
        actual = load_actual()
        expected = load_expected()
        assert rel_close(
            actual["diagnostics"]["max_displacement_m"],
            expected["diagnostics"]["max_displacement_m"]
        )

    def test_total_radiation_loss(self):
        """Verify total radiation heat loss matches expected value."""
        actual = load_actual()
        expected = load_expected()
        assert rel_close(
            actual["diagnostics"]["total_radiation_loss"],
            expected["diagnostics"]["total_radiation_loss"]
        ), (
            f"Radiation loss: got {actual['diagnostics']['total_radiation_loss']:.4e}, "
            f"expected {expected['diagnostics']['total_radiation_loss']:.4e}"
        )

    def test_temperature_profile_length(self):
        """Verify temperature profile has correct number of cells."""
        actual = load_actual()
        expected = load_expected()
        assert len(actual["profiles"]["temperature_K"]) == len(expected["profiles"]["temperature_K"])

    def test_temperature_profile_values(self):
        """Verify temperature at each cell matches expected."""
        actual = load_actual()
        expected = load_expected()
        for i, (act, exp) in enumerate(zip(
            actual["profiles"]["temperature_K"],
            expected["profiles"]["temperature_K"]
        )):
            if abs(exp) > 1e-10:
                assert rel_close(act, exp), (
                    f"Temperature at cell {i}: got {act:.4f}, expected {exp:.4f}"
                )

    def test_stress_profile_values(self):
        """Verify thermal stress at each cell matches expected."""
        actual = load_actual()
        expected = load_expected()
        for i, (act, exp) in enumerate(zip(
            actual["profiles"]["thermal_stress_Pa"],
            expected["profiles"]["thermal_stress_Pa"]
        )):
            if abs(exp) > 1e-6:
                assert rel_close(act, exp), (
                    f"Stress at cell {i}: got {act:.4e}, expected {exp:.4e}"
                )

    def test_displacement_profile_values(self):
        """Verify displacement at each cell matches expected."""
        actual = load_actual()
        expected = load_expected()
        for i, (act, exp) in enumerate(zip(
            actual["profiles"]["displacement_m"],
            expected["profiles"]["displacement_m"]
        )):
            if abs(exp) > 1e-15:
                assert rel_close(act, exp), (
                    f"Displacement at cell {i}: got {act:.6e}, expected {exp:.6e}"
                )

    def test_energy_balance(self):
        """Verify energy balance error is consistent."""
        actual = load_actual()
        expected = load_expected()
        assert rel_close(
            actual["diagnostics"]["energy_balance_error"],
            expected["diagnostics"]["energy_balance_error"]
        )
