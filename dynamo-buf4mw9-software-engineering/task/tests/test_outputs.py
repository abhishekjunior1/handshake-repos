"""Test suite for PLC historian migration pipeline output validation.

Compares the actual pipeline output against expected output to verify
correct processing of all tag types including discrete/boolean tags,
tags with various scan rates, and multi-sample quality batches.
"""
import json
import os
import pytest

EXPECTED_PATH = '/tests/expected_output.json'
OUTPUT_PATH = '/app/output.json'


def load_json(path):
    """Load and parse a JSON file."""
    with open(path, 'r') as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected output fixture."""
    assert os.path.exists(EXPECTED_PATH), f"Expected output not found: {EXPECTED_PATH}"
    return load_json(EXPECTED_PATH)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    assert os.path.exists(OUTPUT_PATH), f"Pipeline output not found: {OUTPUT_PATH}"
    return load_json(OUTPUT_PATH)


class TestMetadata:
    """Tests for output metadata structure and values."""

    def test_metadata_present(self, actual_output):
        """Verify the output contains a metadata section."""
        assert 'metadata' in actual_output, "Output missing 'metadata' key"

    def test_source_format(self, actual_output, expected_output):
        """Verify the source format identifier matches expected."""
        assert actual_output['metadata']['source_format'] == expected_output['metadata']['source_format']

    def test_migration_version(self, actual_output, expected_output):
        """Verify the migration version string matches expected."""
        assert actual_output['metadata']['migration_version'] == expected_output['metadata']['migration_version']

    def test_tag_count(self, actual_output, expected_output):
        """Verify the reported tag count matches the number of processed tags."""
        assert actual_output['metadata']['tag_count'] == expected_output['metadata']['tag_count']

    def test_total_samples(self, actual_output, expected_output):
        """Verify the total sample count across all tags matches expected."""
        assert actual_output['metadata']['total_samples'] == expected_output['metadata']['total_samples']


class TestTagStructure:
    """Tests for correct tag array structure and counts."""

    def test_tags_key_present(self, actual_output):
        """Verify the output contains a tags array."""
        assert 'tags' in actual_output, "Output missing 'tags' key"

    def test_correct_tag_count(self, actual_output, expected_output):
        """Verify the number of tag entries matches expected."""
        assert len(actual_output['tags']) == len(expected_output['tags'])

    def test_tag_ids(self, actual_output, expected_output):
        """Verify each tag has the correct tag_id."""
        for i, (actual, expected) in enumerate(zip(actual_output['tags'], expected_output['tags'])):
            assert actual['tag_id'] == expected['tag_id'], f"Tag {i} id mismatch"

    def test_tag_types(self, actual_output, expected_output):
        """Verify each tag reports its correct type (analog/discrete)."""
        for i, (actual, expected) in enumerate(zip(actual_output['tags'], expected_output['tags'])):
            assert actual['tag_type'] == expected['tag_type'], f"Tag {i} type mismatch"

    def test_sample_counts(self, actual_output, expected_output):
        """Verify each tag has the correct number of output samples."""
        for i, (actual, expected) in enumerate(zip(actual_output['tags'], expected_output['tags'])):
            assert actual['sample_count'] == expected['sample_count'], (
                f"Tag {i} sample count: got {actual['sample_count']}, "
                f"expected {expected['sample_count']}"
            )

    def test_calibration_applied(self, actual_output, expected_output):
        """Verify each tag reports calibration_applied status correctly."""
        for i, (actual, expected) in enumerate(zip(actual_output['tags'], expected_output['tags'])):
            assert actual['calibration_applied'] == expected['calibration_applied'], (
                f"Tag {i} calibration_applied mismatch"
            )


class TestDiscreteTagInterpolation:
    """Tests for correct interpolation of discrete (boolean/state) tags."""

    def test_discrete_tag_values(self, actual_output, expected_output):
        """Verify discrete tag interpolated values use stepped (zero-order hold) mode.

        A discrete tag representing a boolean state should hold its previous
        value during gaps rather than linearly interpolating between states.
        """
        tag_idx = 0  # First tag is discrete
        actual_samples = actual_output['tags'][tag_idx]['samples']
        expected_samples = expected_output['tags'][tag_idx]['samples']
        assert len(actual_samples) == len(expected_samples), (
            f"Discrete tag sample count: got {len(actual_samples)}, "
            f"expected {len(expected_samples)}"
        )
        for j, (actual, expected) in enumerate(zip(actual_samples, expected_samples)):
            assert actual['value'] == expected['value'], (
                f"Discrete tag sample {j}: got {actual['value']}, "
                f"expected {expected['value']}"
            )

    def test_discrete_interpolated_holds_value(self, actual_output, expected_output):
        """Verify that interpolated points in discrete tag hold the previous state.

        Linear interpolation would produce fractional values (e.g., 0.5 between
        ON=1 and OFF=0), which is incorrect for a discrete/boolean signal.
        """
        tag_idx = 0
        actual_samples = actual_output['tags'][tag_idx]['samples']
        interp_samples = [s for s in actual_samples if s['interpolated']]
        assert len(interp_samples) == 1, (
            f"Expected exactly 1 interpolated sample in discrete tag, got {len(interp_samples)}"
        )
        assert interp_samples[0]['value'] == expected_output['tags'][tag_idx]['samples'][1]['value']


class TestGapDetection:
    """Tests for correct gap detection with tag-specific thresholds."""

    def test_fast_scan_tag_gap_detected(self, actual_output, expected_output):
        """Verify that gaps shorter than the default threshold are detected
        when the tag's scan rate warrants a tighter threshold.

        A tag scanning at 500ms should detect a 3-second gap (> 3×500ms = 1.5s)
        even though 3s < the default 5s threshold.
        """
        tag_idx = 1  # Second tag has 500ms scan rate
        actual_count = actual_output['tags'][tag_idx]['sample_count']
        expected_count = expected_output['tags'][tag_idx]['sample_count']
        assert actual_count == expected_count, (
            f"Fast-scan tag should have interpolated samples: "
            f"got {actual_count}, expected {expected_count}"
        )

    def test_fast_scan_tag_interpolated_value(self, actual_output, expected_output):
        """Verify the interpolated value in the fast-scan tag gap is correct.

        Linear interpolation between 5000 and 6000 at the midpoint should
        produce 5500.
        """
        tag_idx = 1
        actual_samples = actual_output['tags'][tag_idx]['samples']
        expected_samples = expected_output['tags'][tag_idx]['samples']
        for j, (actual, expected) in enumerate(zip(actual_samples, expected_samples)):
            assert actual['value'] == expected['value'], (
                f"Tag 2 sample {j}: got {actual['value']}, expected {expected['value']}"
            )

    def test_fast_scan_tag_interpolated_flag(self, actual_output, expected_output):
        """Verify exactly one interpolated sample exists in the fast-scan tag."""
        tag_idx = 1
        actual_samples = actual_output['tags'][tag_idx]['samples']
        interp_samples = [s for s in actual_samples if s['interpolated']]
        assert len(interp_samples) == 1, (
            f"Expected exactly 1 interpolated sample in fast-scan tag, got {len(interp_samples)}"
        )

    def test_tags_0_1_timestamps(self, actual_output, expected_output):
        """Verify timestamp_iso values are correct for tags 0 and 1."""
        for i in [0, 1]:
            actual_ts = [s['timestamp_iso'] for s in actual_output['tags'][i]['samples']]
            expected_ts = [s['timestamp_iso'] for s in expected_output['tags'][i]['samples']]
            assert actual_ts == expected_ts, f"Tag {i} timestamp_iso mismatch"


class TestQualityPropagation:
    """Tests for correct quality severity propagation."""

    def test_tag3_quality_severities(self, actual_output, expected_output):
        """Verify quality severity values for the multi-sample tag.

        The historian backfill quality propagation model applies retroactive
        annotations in reverse-chronological order.
        """
        tag_idx = 2
        actual_samples = actual_output['tags'][tag_idx]['samples']
        expected_samples = expected_output['tags'][tag_idx]['samples']
        for j, (actual, expected) in enumerate(zip(actual_samples, expected_samples)):
            assert actual['quality_severity'] == expected['quality_severity'], (
                f"Tag 3 sample {j} quality: got {actual['quality_severity']}, "
                f"expected {expected['quality_severity']}"
            )


class TestTimestampOrdering:
    """Tests for correct timestamp handling in output."""

    def test_tag3_preserves_source_order(self, actual_output, expected_output):
        """Verify that non-monotonic timestamps are preserved in output order.

        The archive format stores samples in block order, not time order.
        Output must preserve source ordering for audit trail compliance.
        """
        tag_idx = 2
        actual_timestamps = [s['timestamp_iso'] for s in actual_output['tags'][tag_idx]['samples']]
        expected_timestamps = [s['timestamp_iso'] for s in expected_output['tags'][tag_idx]['samples']]
        assert actual_timestamps == expected_timestamps, (
            f"Tag 3 timestamp order mismatch"
        )

    def test_tag3_sample_count(self, actual_output, expected_output):
        """Verify tag 3 has correct number of samples including any interpolated points."""
        tag_idx = 2
        assert actual_output['tags'][tag_idx]['sample_count'] == expected_output['tags'][tag_idx]['sample_count']
