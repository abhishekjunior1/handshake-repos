"""
Tests for DMA scatter-gather descriptor chain migration pipeline.

Validates that the migrated output matches expected values by comparing
the pipeline output against pre-computed expected results on hidden data.
"""

import json
import math
import pytest


EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def expected_output():
    """Load the expected output for comparison."""
    with open(EXPECTED_OUTPUT_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    with open(ACTUAL_OUTPUT_PATH, "r") as f:
        return json.load(f)


class TestMigrationSummary:
    """Tests for the migration summary section of the output."""

    def test_descriptor_count(self, actual_output, expected_output):
        """Verify the correct number of descriptors were migrated."""
        assert actual_output["migration_summary"]["descriptor_count"] == \
               expected_output["migration_summary"]["descriptor_count"]

    def test_total_original_bytes(self, actual_output, expected_output):
        """Verify total original transfer bytes are reported correctly."""
        assert actual_output["migration_summary"]["total_original_bytes"] == \
               expected_output["migration_summary"]["total_original_bytes"]

    def test_total_aligned_bytes(self, actual_output, expected_output):
        """Verify total aligned bytes reflect correct alignment calculations."""
        assert actual_output["migration_summary"]["total_aligned_bytes"] == \
               expected_output["migration_summary"]["total_aligned_bytes"]

    def test_alignment_efficiency(self, actual_output, expected_output):
        """Verify alignment efficiency percentage is computed correctly."""
        assert abs(actual_output["migration_summary"]["alignment_efficiency_percent"] -
                   expected_output["migration_summary"]["alignment_efficiency_percent"]) < 0.01

    def test_descriptor_size(self, actual_output, expected_output):
        """Verify target descriptor size includes metadata overhead."""
        assert actual_output["migration_summary"]["descriptor_size"] == \
               expected_output["migration_summary"]["descriptor_size"]

    def test_table_footprint(self, actual_output, expected_output):
        """Verify table footprint calculation is correct."""
        assert actual_output["migration_summary"]["table_footprint_bytes"] == \
               expected_output["migration_summary"]["table_footprint_bytes"]


class TestAddressTranslation:
    """Tests for address translation correctness."""

    def test_bus_width_used(self, actual_output, expected_output):
        """Verify the correct bus width was used for address translation."""
        assert actual_output["address_translation"]["bus_width_used"] == \
               expected_output["address_translation"]["bus_width_used"]

    def test_translated_addresses(self, actual_output, expected_output):
        """Verify all descriptor addresses are correctly translated to byte-space."""
        for i, (actual_desc, expected_desc) in enumerate(zip(
            actual_output["migrated_descriptors"],
            expected_output["migrated_descriptors"]
        )):
            assert actual_desc["translated_address"] == expected_desc["translated_address"], \
                f"Descriptor {i}: translated address mismatch"

    def test_address_span(self, actual_output, expected_output):
        """Verify the computed address span matches expected values."""
        actual_span = actual_output["address_translation"]["address_span"]
        expected_span = expected_output["address_translation"]["address_span"]
        assert actual_span["min_address"] == expected_span["min_address"]
        assert actual_span["max_address"] == expected_span["max_address"]
        assert actual_span["total_span"] == expected_span["total_span"]

    def test_address_map(self, actual_output, expected_output):
        """Verify the per-descriptor address map entries including alignment validity."""
        actual_map = actual_output["address_translation"]["address_map"]
        expected_map = expected_output["address_translation"]["address_map"]
        assert len(actual_map) == len(expected_map), "Address map length mismatch"
        for i, (actual_entry, expected_entry) in enumerate(zip(actual_map, expected_map)):
            assert actual_entry["original_address"] == expected_entry["original_address"], \
                f"Descriptor {i}: original_address mismatch"
            assert actual_entry["translated_address"] == expected_entry["translated_address"], \
                f"Descriptor {i}: translated_address mismatch in address_map"
            assert actual_entry["alignment_valid"] == expected_entry["alignment_valid"], \
                f"Descriptor {i}: alignment_valid mismatch"


class TestBurstScheduling:
    """Tests for burst parameter computation."""

    def test_total_beats(self, actual_output, expected_output):
        """Verify total bus beats are computed from aligned transfer lengths."""
        assert actual_output["bus_performance"]["total_beats"] == \
               expected_output["bus_performance"]["total_beats"]

    def test_total_bursts(self, actual_output, expected_output):
        """Verify burst count reflects aligned transfer sizes."""
        assert actual_output["bus_performance"]["total_bursts"] == \
               expected_output["bus_performance"]["total_bursts"]

    def test_effective_cycles(self, actual_output, expected_output):
        """Verify effective cycle count includes burst overhead."""
        assert actual_output["bus_performance"]["effective_cycles"] == \
               expected_output["bus_performance"]["effective_cycles"]

    def test_overhead_cycles(self, actual_output, expected_output):
        """Verify overhead cycles count (one address-phase cycle per burst)."""
        assert actual_output["bus_performance"]["overhead_cycles"] == \
               expected_output["bus_performance"]["overhead_cycles"]

    def test_boundary_warnings(self, actual_output, expected_output):
        """Verify 4KB boundary crossing warnings are correctly detected."""
        assert actual_output["bus_performance"]["boundary_warnings"] == \
               expected_output["bus_performance"]["boundary_warnings"]

    def test_per_descriptor_burst_params(self, actual_output, expected_output):
        """Verify each descriptor's burst parameters match expected values."""
        for i, (actual_desc, expected_desc) in enumerate(zip(
            actual_output["migrated_descriptors"],
            expected_output["migrated_descriptors"]
        )):
            actual_bp = actual_desc["burst_parameters"]
            expected_bp = expected_desc["burst_parameters"]
            assert actual_bp["burst_length"] == expected_bp["burst_length"], \
                f"Descriptor {i}: burst_length mismatch"
            assert actual_bp["total_beats"] == expected_bp["total_beats"], \
                f"Descriptor {i}: total_beats mismatch"
            assert actual_bp["full_bursts"] == expected_bp["full_bursts"], \
                f"Descriptor {i}: full_bursts mismatch"


class TestChainLinkage:
    """Tests for descriptor chain link computation."""

    def test_base_address(self, actual_output, expected_output):
        """Verify chain base address matches migration configuration."""
        assert actual_output["chain_linkage"]["base_address"] == \
               expected_output["chain_linkage"]["base_address"]

    def test_chain_links(self, actual_output, expected_output):
        """Verify all chain_next pointers are computed with correct base address."""
        for i, (actual_desc, expected_desc) in enumerate(zip(
            actual_output["migrated_descriptors"],
            expected_output["migrated_descriptors"]
        )):
            assert actual_desc["chain_next"] == expected_desc["chain_next"], \
                f"Descriptor {i}: chain_next mismatch (0x{actual_desc['chain_next']:X} " \
                f"vs expected 0x{expected_desc['chain_next']:X})"

    def test_links_valid(self, actual_output, expected_output):
        """Verify chain link validation passes."""
        assert actual_output["chain_linkage"]["links_valid"] == \
               expected_output["chain_linkage"]["links_valid"]

    def test_table_layout(self, actual_output, expected_output):
        """Verify descriptor table layout uses correct base address."""
        actual_layout = actual_output["chain_linkage"]["table_layout"]
        expected_layout = expected_output["chain_linkage"]["table_layout"]
        for i, (actual_entry, expected_entry) in enumerate(zip(actual_layout, expected_layout)):
            assert actual_entry["start_address"] == expected_entry["start_address"], \
                f"Descriptor {i}: table start_address mismatch"


class TestValidation:
    """Tests for migration validation results."""

    def test_overall_valid(self, actual_output, expected_output):
        """Verify overall validation status matches."""
        assert actual_output["validation"]["overall_valid"] == \
               expected_output["validation"]["overall_valid"]

    def test_checks_passed(self, actual_output, expected_output):
        """Verify the number of passed validation checks."""
        assert actual_output["validation"]["checks_passed"] == \
               expected_output["validation"]["checks_passed"]

    def test_capacity_utilization(self, actual_output, expected_output):
        """Verify capacity utilization percentage is computed correctly."""
        assert abs(actual_output["validation"]["capacity_utilization_percent"] -
                   expected_output["validation"]["capacity_utilization_percent"]) < 0.01

    def test_boundary_violations(self, actual_output, expected_output):
        """Verify 4KB boundary violation detection reports correct descriptors and addresses."""
        assert actual_output["validation"]["boundary_violations"] == \
               expected_output["validation"]["boundary_violations"]


class TestMigratedDescriptors:
    """Tests for individual migrated descriptor properties."""

    def test_descriptor_count_matches(self, actual_output, expected_output):
        """Verify the number of output descriptors matches expected."""
        assert len(actual_output["migrated_descriptors"]) == \
               len(expected_output["migrated_descriptors"])

    def test_aligned_transfer_lengths(self, actual_output, expected_output):
        """Verify aligned transfer lengths are correctly computed."""
        for i, (actual_desc, expected_desc) in enumerate(zip(
            actual_output["migrated_descriptors"],
            expected_output["migrated_descriptors"]
        )):
            assert actual_desc["aligned_transfer_length"] == \
                   expected_desc["aligned_transfer_length"], \
                f"Descriptor {i}: aligned_transfer_length mismatch"

    def test_original_fields_preserved(self, actual_output, expected_output):
        """Verify original descriptor fields are preserved unchanged."""
        for i, (actual_desc, expected_desc) in enumerate(zip(
            actual_output["migrated_descriptors"],
            expected_output["migrated_descriptors"]
        )):
            assert actual_desc["original_source_address"] == \
                   expected_desc["original_source_address"]
            assert actual_desc["original_transfer_length"] == \
                   expected_desc["original_transfer_length"]
            assert actual_desc["control_flags"] == expected_desc["control_flags"]
            assert actual_desc["priority_level"] == expected_desc["priority_level"]
