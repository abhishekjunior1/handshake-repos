"""Verification tests for DSP pipeline output."""

import json
import os


def load_output():
    """Load the pipeline output."""
    with open("/app/output.json", 'r') as f:
        return json.load(f)


def load_expected():
    """Load the expected output."""
    with open("/tests/expected_output.json", 'r') as f:
        return json.load(f)


def approx_equal(actual, expected, rel_tol=1e-4):
    """Check approximate equality with relative tolerance."""
    if expected == 0:
        return abs(actual) < 1e-10
    return abs(actual - expected) / abs(expected) <= rel_tol


def test_output_file_exists():
    """Verify output.json was produced."""
    assert os.path.exists("/app/output.json")


def test_output_structure():
    """Verify all required top-level sections exist."""
    output = load_output()
    for key in ['analysis_parameters', 'spectral_analysis', 'signal_quality', 'filter_characteristics', 'segment_info']:
        assert key in output, f"Missing: {key}"


def test_total_power():
    """Verify total integrated power from averaged PSD."""
    output = load_output()
    expected = load_expected()
    actual = output['spectral_analysis']['total_power']
    exp_val = expected['spectral_analysis']['total_power']
    assert approx_equal(actual, exp_val, rel_tol=1e-3), \
        f"total_power: {actual} vs expected {exp_val}"


def test_peak_frequency():
    """Verify peak frequency detection."""
    output = load_output()
    expected = load_expected()
    actual = output['spectral_analysis']['peak_frequency']
    exp_val = expected['spectral_analysis']['peak_frequency']
    assert approx_equal(actual, exp_val, rel_tol=1e-4), \
        f"peak_frequency: {actual} vs {exp_val}"


def test_peak_power():
    """Verify peak power density value."""
    output = load_output()
    expected = load_expected()
    actual = output['spectral_analysis']['peak_power']
    exp_val = expected['spectral_analysis']['peak_power']
    assert approx_equal(actual, exp_val, rel_tol=1e-3), \
        f"peak_power: {actual} vs {exp_val}"


def test_spectral_centroid():
    """Verify spectral centroid from averaged PSD."""
    output = load_output()
    expected = load_expected()
    actual = output['spectral_analysis']['spectral_centroid']
    exp_val = expected['spectral_analysis']['spectral_centroid']
    assert approx_equal(actual, exp_val, rel_tol=1e-2), \
        f"spectral_centroid: {actual} vs {exp_val}"


def test_spectral_bandwidth():
    """Verify spectral bandwidth from averaged PSD."""
    output = load_output()
    expected = load_expected()
    actual = output['spectral_analysis']['spectral_bandwidth']
    exp_val = expected['spectral_analysis']['spectral_bandwidth']
    assert approx_equal(actual, exp_val, rel_tol=1e-2), \
        f"spectral_bandwidth: {actual} vs {exp_val}"


def test_spectral_flatness():
    """Verify spectral flatness measure from averaged PSD."""
    output = load_output()
    expected = load_expected()
    actual = output['spectral_analysis']['spectral_flatness']
    exp_val = expected['spectral_analysis']['spectral_flatness']
    assert approx_equal(actual, exp_val, rel_tol=1e-2), \
        f"spectral_flatness: {actual} vs {exp_val}"


def test_snr_db():
    """Verify signal-to-noise ratio."""
    output = load_output()
    expected = load_expected()
    actual = output['signal_quality']['snr_db']
    exp_val = expected['signal_quality']['snr_db']
    assert approx_equal(actual, exp_val, rel_tol=1e-3), \
        f"snr_db: {actual} vs {exp_val}"


def test_signal_power():
    """Verify absolute signal power in the band."""
    output = load_output()
    expected = load_expected()
    actual = output['signal_quality']['signal_power']
    exp_val = expected['signal_quality']['signal_power']
    assert approx_equal(actual, exp_val, rel_tol=1e-3), \
        f"signal_power: {actual} vs {exp_val}"


def test_effective_band_power():
    """Verify overlap-normalized effective band power."""
    output = load_output()
    expected = load_expected()
    actual = output['signal_quality']['effective_band_power']
    exp_val = expected['signal_quality']['effective_band_power']
    assert approx_equal(actual, exp_val, rel_tol=1e-3), \
        f"effective_band_power: {actual} vs {exp_val}"


def test_filter_bandwidth():
    """Verify filter -3dB bandwidth."""
    output = load_output()
    expected = load_expected()
    actual = output['filter_characteristics']['bandwidth_3db']
    exp_val = expected['filter_characteristics']['bandwidth_3db']
    assert approx_equal(actual, exp_val, rel_tol=1e-3), \
        f"bandwidth_3db: {actual} vs {exp_val}"


def test_segment_count():
    """Verify correct segment count is reported."""
    output = load_output()
    expected = load_expected()
    assert output['segment_info']['n_segments'] == expected['segment_info']['n_segments'], \
        f"n_segments: {output['segment_info']['n_segments']} vs {expected['segment_info']['n_segments']}"
