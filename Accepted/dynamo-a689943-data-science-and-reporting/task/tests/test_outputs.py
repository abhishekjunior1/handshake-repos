"""Tests for the spectral anomaly detection pipeline output.

Verifies that the pipeline correctly handles non-stationary time series
with tapered windows, per-segment thresholding, and proper effective
sample size normalization.
"""

import json
import os
import math

EXPECTED_PATH = "/tests/expected_output.json"
OUTPUT_PATH = "/app/output.json"


def load_output():
    """Load the pipeline output JSON."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output JSON."""
    assert os.path.exists(EXPECTED_PATH), f"Expected output not found at {EXPECTED_PATH}"
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def test_output_file_exists():
    """Verify that the pipeline produces an output file at the expected path."""
    assert os.path.exists(OUTPUT_PATH), "Pipeline did not produce output.json"


def test_output_is_valid_json():
    """Verify that the output file contains valid JSON with required structure."""
    output = load_output()
    required_keys = ['summary', 'segments', 'anomalies', 'spectral', 'config']
    for key in required_keys:
        assert key in output, f"Missing required key: {key}"


def test_summary_anomaly_count():
    """Verify the total number of detected anomalies matches expected."""
    output = load_output()
    expected = load_expected()
    assert output['summary']['n_anomalies'] == expected['summary']['n_anomalies'], (
        f"Anomaly count wrong: got {output['summary']['n_anomalies']}, "
        f"expected {expected['summary']['n_anomalies']}"
    )


def test_summary_anomaly_rate():
    """Verify the anomaly rate is correctly computed."""
    output = load_output()
    expected = load_expected()
    assert abs(output['summary']['anomaly_rate'] - expected['summary']['anomaly_rate']) < 1e-6, (
        f"Anomaly rate wrong: got {output['summary']['anomaly_rate']}, "
        f"expected {expected['summary']['anomaly_rate']}"
    )


def test_segment_count():
    """Verify the correct number of segments is detected."""
    output = load_output()
    expected = load_expected()
    assert output['summary']['n_segments'] == expected['summary']['n_segments'], (
        f"Segment count wrong: got {output['summary']['n_segments']}, "
        f"expected {expected['summary']['n_segments']}"
    )


def test_per_segment_thresholds():
    """Verify that each segment has the correct anomaly threshold."""
    output = load_output()
    expected = load_expected()
    for i, (out_seg, exp_seg) in enumerate(zip(output['segments'], expected['segments'])):
        assert abs(out_seg['threshold'] - exp_seg['threshold']) < 1e-4, (
            f"Segment {i} threshold wrong: got {out_seg['threshold']}, "
            f"expected {exp_seg['threshold']}"
        )


def test_per_segment_anomaly_counts():
    """Verify per-segment anomaly counts match expected values."""
    output = load_output()
    expected = load_expected()
    for i, (out_seg, exp_seg) in enumerate(zip(output['segments'], expected['segments'])):
        assert out_seg['n_anomalies'] == exp_seg['n_anomalies'], (
            f"Segment {i} anomaly count wrong: got {out_seg['n_anomalies']}, "
            f"expected {exp_seg['n_anomalies']}"
        )


def test_anomaly_list():
    """Verify the list of detected anomalies matches expected exactly."""
    output = load_output()
    expected = load_expected()
    assert output['anomalies'] == expected['anomalies'], (
        f"Anomaly list differs: got {len(output['anomalies'])} anomalies, "
        f"expected {len(expected['anomalies'])}"
    )


def test_spectral_per_segment_info():
    """Verify spectral analysis metadata per segment."""
    output = load_output()
    expected = load_expected()
    assert len(output['spectral']['per_segment']) == len(expected['spectral']['per_segment']), (
        "Different number of spectral summaries"
    )
    for i, (out_s, exp_s) in enumerate(zip(
        output['spectral']['per_segment'], expected['spectral']['per_segment']
    )):
        assert out_s['ar_order'] == exp_s['ar_order'], (
            f"Segment {i} AR order wrong: got {out_s['ar_order']}, expected {exp_s['ar_order']}"
        )


def test_total_observations():
    """Verify total observation count in output."""
    output = load_output()
    expected = load_expected()
    assert output['summary']['total_observations'] == expected['summary']['total_observations'], (
        f"Total observations wrong: got {output['summary']['total_observations']}, "
        f"expected {expected['summary']['total_observations']}"
    )


def test_config_preserved():
    """Verify pipeline configuration is correctly recorded in output."""
    output = load_output()
    expected = load_expected()
    assert output['config']['window_type'] == expected['config']['window_type']
    assert output['config']['n_segments'] == expected['config']['n_segments']
    assert output['config']['change_points'] == expected['config']['change_points']


def test_severity_statistics():
    """Verify severity statistics match expected values."""
    output = load_output()
    expected = load_expected()
    assert abs(output['summary']['mean_severity'] - expected['summary']['mean_severity']) < 1e-4, (
        f"Mean severity wrong: got {output['summary']['mean_severity']}, "
        f"expected {expected['summary']['mean_severity']}"
    )
    assert abs(output['summary']['max_severity'] - expected['summary']['max_severity']) < 1e-4, (
        f"Max severity wrong: got {output['summary']['max_severity']}, "
        f"expected {expected['summary']['max_severity']}"
    )


def test_full_output_match():
    """Verify that the entire output matches the expected output."""
    output = load_output()
    expected = load_expected()
    assert output == expected, "Full output does not match expected."
