"""
Verification tests for the feature flag evaluation pipeline.

Compares the pipeline output against expected results for flag evaluations,
summary statistics, and pipeline metadata.
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


class TestEvaluations:
    """Tests for the per-device flag evaluations."""

    def test_all_devices_present(self, output, expected):
        """Verify all expected devices are present in evaluations."""
        assert set(output["evaluations"].keys()) == set(expected["evaluations"].keys())

    def test_all_flags_per_device(self, output, expected):
        """Verify each device has evaluations for all expected flags."""
        for device_id in expected["evaluations"]:
            assert set(output["evaluations"][device_id].keys()) == set(
                expected["evaluations"][device_id].keys()
            ), f"Flag mismatch for device {device_id}"

    def test_enabled_states_match(self, output, expected):
        """Verify enabled/disabled state matches for every device-flag pair."""
        for device_id in expected["evaluations"]:
            for flag_name, exp_eval in expected["evaluations"][device_id].items():
                actual_eval = output["evaluations"][device_id][flag_name]
                assert actual_eval["enabled"] == exp_eval["enabled"], (
                    f"Device {device_id}, flag {flag_name}: "
                    f"got enabled={actual_eval['enabled']}, expected={exp_eval['enabled']}"
                )

    def test_reasons_match(self, output, expected):
        """Verify the evaluation reason matches for every device-flag pair."""
        for device_id in expected["evaluations"]:
            for flag_name, exp_eval in expected["evaluations"][device_id].items():
                actual_eval = output["evaluations"][device_id][flag_name]
                assert actual_eval["reason"] == exp_eval["reason"], (
                    f"Device {device_id}, flag {flag_name}: "
                    f"got reason={actual_eval['reason']}, expected={exp_eval['reason']}"
                )

    def test_total_enabled_count(self, output, expected):
        """Verify the total number of enabled flags matches expected."""
        actual_enabled = sum(
            1 for device_evals in output["evaluations"].values()
            for eval_data in device_evals.values()
            if eval_data["enabled"]
        )
        expected_enabled = sum(
            1 for device_evals in expected["evaluations"].values()
            for eval_data in device_evals.values()
            if eval_data["enabled"]
        )
        assert actual_enabled == expected_enabled

    def test_total_disabled_count(self, output, expected):
        """Verify the total number of disabled flags matches expected."""
        actual_disabled = sum(
            1 for device_evals in output["evaluations"].values()
            for eval_data in device_evals.values()
            if not eval_data["enabled"]
        )
        expected_disabled = sum(
            1 for device_evals in expected["evaluations"].values()
            for eval_data in device_evals.values()
            if not eval_data["enabled"]
        )
        assert actual_disabled == expected_disabled


class TestSummary:
    """Tests for the summary statistics."""

    def test_total_devices(self, output, expected):
        """Verify total device count in summary."""
        assert output["summary"]["total_devices"] == expected["summary"]["total_devices"]

    def test_total_flags(self, output, expected):
        """Verify total flag count in summary."""
        assert output["summary"]["total_flags"] == expected["summary"]["total_flags"]

    def test_total_evaluations(self, output, expected):
        """Verify total evaluation count in summary."""
        assert output["summary"]["total_evaluations"] == expected["summary"]["total_evaluations"]

    def test_enabled_count(self, output, expected):
        """Verify enabled count in summary matches expected."""
        assert output["summary"]["enabled_count"] == expected["summary"]["enabled_count"]

    def test_disabled_count(self, output, expected):
        """Verify disabled count in summary matches expected."""
        assert output["summary"]["disabled_count"] == expected["summary"]["disabled_count"]

    def test_dependency_overrides(self, output, expected):
        """Verify dependency override count matches expected."""
        assert output["summary"]["dependency_overrides"] == expected["summary"]["dependency_overrides"]

    def test_conflict_resolutions(self, output, expected):
        """Verify conflict resolution count matches expected."""
        assert output["summary"]["conflict_resolutions"] == expected["summary"]["conflict_resolutions"]


class TestMetadata:
    """Tests for the pipeline metadata."""

    def test_flags_evaluated(self, output, expected):
        """Verify the list of evaluated flags matches expected."""
        assert output["metadata"]["flags_evaluated"] == expected["metadata"]["flags_evaluated"]

    def test_devices_evaluated(self, output, expected):
        """Verify devices evaluated count matches expected."""
        assert output["metadata"]["devices_evaluated"] == expected["metadata"]["devices_evaluated"]

    def test_mutex_groups_processed(self, output, expected):
        """Verify mutex groups processed count matches expected."""
        assert output["metadata"]["mutex_groups_processed"] == expected["metadata"]["mutex_groups_processed"]

    def test_dependency_chains_resolved(self, output, expected):
        """Verify dependency chains count matches expected."""
        assert output["metadata"]["dependency_chains_resolved"] == expected["metadata"]["dependency_chains_resolved"]

    def test_rollout_hash_method(self, output, expected):
        """Verify the reported rollout hash method matches expected."""
        assert output["metadata"]["rollout_hash_method"] == expected["metadata"]["rollout_hash_method"]
