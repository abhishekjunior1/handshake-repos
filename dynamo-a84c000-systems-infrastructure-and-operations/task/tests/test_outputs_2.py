"""
Test suite for virtio device hotplug controller pipeline output verification.

Compares the pipeline output against expected results for the hidden test
configuration that exercises edge cases in capability negotiation, DMA
mapping, and queue management.
"""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output_2.json")
OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def expected_output():
    """Load the expected output JSON."""
    with open(EXPECTED_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output JSON."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


def test_pipeline_status(actual_output, expected_output):
    """Verify the pipeline reports successful completion status."""
    assert actual_output["pipeline_status"] == expected_output["pipeline_status"]


def test_device_registry_count(actual_output, expected_output):
    """Verify the correct number of devices are registered."""
    actual_reg = actual_output["stages"]["device_registry"]
    expected_reg = expected_output["stages"]["device_registry"]
    assert actual_reg["device_count"] == expected_reg["device_count"]


def test_device_final_state(actual_output, expected_output):
    """Verify all devices reach the expected final lifecycle state."""
    actual_devices = actual_output["stages"]["device_registry"]["devices"]
    expected_devices = expected_output["stages"]["device_registry"]["devices"]
    for device_id, expected_dev in expected_devices.items():
        assert device_id in actual_devices
        assert actual_devices[device_id]["current_state"] == expected_dev["current_state"]


def test_device_state_history(actual_output, expected_output):
    """Verify the complete state transition history for each device."""
    actual_devices = actual_output["stages"]["device_registry"]["devices"]
    expected_devices = expected_output["stages"]["device_registry"]["devices"]
    for device_id, expected_dev in expected_devices.items():
        assert actual_devices[device_id]["state_history"] == expected_dev["state_history"]


def test_negotiated_feature_count(actual_output, expected_output):
    """Verify the number of successfully negotiated features."""
    actual_neg = actual_output["stages"]["capability_negotiation"]
    expected_neg = expected_output["stages"]["capability_negotiation"]
    assert actual_neg["negotiated_feature_count"] == expected_neg["negotiated_feature_count"]


def test_negotiated_features_list(actual_output, expected_output):
    """Verify the exact set of negotiated feature bits."""
    actual_neg = actual_output["stages"]["capability_negotiation"]
    expected_neg = expected_output["stages"]["capability_negotiation"]
    assert actual_neg["negotiated_features"] == expected_neg["negotiated_features"]


def test_rejected_features(actual_output, expected_output):
    """Verify features correctly identified as unsupported by guest."""
    actual_neg = actual_output["stages"]["capability_negotiation"]
    expected_neg = expected_output["stages"]["capability_negotiation"]
    assert actual_neg["rejected_features"] == expected_neg["rejected_features"]


def test_queue_effective_depth(actual_output, expected_output):
    """Verify queue depth is calculated from the correct feature set."""
    actual_q = actual_output["stages"]["queue_configuration"]
    expected_q = expected_output["stages"]["queue_configuration"]
    assert actual_q["effective_depth"] == expected_q["effective_depth"]


def test_queue_avail_idx(actual_output, expected_output):
    """Verify the available ring index uses correct 16-bit wrapping."""
    actual_q = actual_output["stages"]["queue_configuration"]
    expected_q = expected_output["stages"]["queue_configuration"]
    actual_avail = actual_q["queues"][0]["avail_idx"]
    expected_avail = expected_q["queues"][0]["avail_idx"]
    assert actual_avail == expected_avail


def test_queue_submission_count(actual_output, expected_output):
    """Verify all descriptors were submitted successfully."""
    actual_sub = actual_output["stages"]["queue_configuration"]["submission_result"]
    expected_sub = expected_output["stages"]["queue_configuration"]["submission_result"]
    assert actual_sub["submitted"] == expected_sub["submitted"]
    assert actual_sub["current_avail_idx"] == expected_sub["current_avail_idx"]


def test_queue_submission_details(actual_output, expected_output):
    """Verify individual descriptor submission ring positions."""
    actual_sub = actual_output["stages"]["queue_configuration"]["submission_result"]
    expected_sub = expected_output["stages"]["queue_configuration"]["submission_result"]
    assert actual_sub["submissions"] == expected_sub["submissions"]


def test_dma_total_mappings(actual_output, expected_output):
    """Verify correct number of IOMMU page table entries created."""
    actual_dma = actual_output["stages"]["dma_mappings"]
    expected_dma = expected_output["stages"]["dma_mappings"]
    assert actual_dma["total_mappings"] == expected_dma["total_mappings"]


def test_dma_total_mapped_bytes(actual_output, expected_output):
    """Verify total mapped memory matches expected allocation."""
    actual_dma = actual_output["stages"]["dma_mappings"]
    expected_dma = expected_output["stages"]["dma_mappings"]
    assert actual_dma["total_mapped_bytes"] == expected_dma["total_mapped_bytes"]


def test_dma_mapping_page_size(actual_output, expected_output):
    """Verify DMA mappings use the correct page size granularity."""
    actual_dma = actual_output["stages"]["dma_mappings"]
    expected_dma = expected_output["stages"]["dma_mappings"]
    for actual_region, expected_region in zip(actual_dma["regions"], expected_dma["regions"]):
        assert actual_region["mapping_page_size"] == expected_region["mapping_page_size"]


def test_dma_region_page_counts(actual_output, expected_output):
    """Verify each DMA region has the correct number of page mappings."""
    actual_dma = actual_output["stages"]["dma_mappings"]
    expected_dma = expected_output["stages"]["dma_mappings"]
    for actual_region, expected_region in zip(actual_dma["regions"], expected_dma["regions"]):
        assert actual_region["page_count"] == expected_region["page_count"]


def test_migration_state(actual_output, expected_output):
    """Verify migration subsystem state matches expected configuration."""
    actual_mig = actual_output["stages"]["migration_state"]
    expected_mig = expected_output["stages"]["migration_state"]
    assert actual_mig["migration_active"] == expected_mig["migration_active"]
    assert actual_mig["dirty_page_count"] == expected_mig["dirty_page_count"]


def test_migration_dirty_ratio(actual_output, expected_output):
    """Verify dirty page ratio calculation is correct."""
    actual_mig = actual_output["stages"]["migration_state"]
    expected_mig = expected_output["stages"]["migration_state"]
    assert abs(actual_mig["dirty_ratio"] - expected_mig["dirty_ratio"]) < 1e-10


def test_full_output_match(actual_output, expected_output):
    """Verify the complete pipeline output matches expected results exactly."""
    assert actual_output == expected_output
