"""Tests for the spectral anomaly detection pipeline.

Validates that the pipeline correctly computes periodograms, fits spectral
envelopes, whitens series, scores observations for anomalousness, and
produces per-segment anomaly classifications with appropriate thresholds.
"""

import json
import math

EXPECTED_PATH = '/tests/expected_output.json'
OUTPUT_PATH = '/app/output.json'


def load_outputs():
    """Load expected and actual output files."""
    with open(EXPECTED_PATH, 'r') as f:
        expected = json.load(f)
    with open(OUTPUT_PATH, 'r') as f:
        actual = json.load(f)
    return expected, actual


def approx_equal(a, b, rel_tol=1e-3, abs_tol=1e-6):
    """Check if two values are approximately equal."""
    if a == b:
        return True
    if abs(a) < abs_tol and abs(b) < abs_tol:
        return True
    return abs(a - b) <= max(rel_tol * max(abs(a), abs(b)), abs_tol)


class TestAnomalyScores:
    """Tests for per-observation anomaly scoring accuracy."""

    def test_anomaly_scores_length(self):
        """Verify the correct number of anomaly scores are produced."""
        expected, actual = load_outputs()
        assert len(actual['anomaly_scores']) == len(expected['anomaly_scores']), \
            f"Expected {len(expected['anomaly_scores'])} scores, got {len(actual['anomaly_scores'])}"

    def test_anomaly_scores_values(self):
        """Verify anomaly scores match expected values from correct normalization."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['anomaly_scores'], actual['anomaly_scores'])):
            assert approx_equal(act, exp), \
                f"Score[{i}]: expected {exp:.6f}, got {act:.6f}"

    def test_overall_anomaly_score(self):
        """Verify the aggregate anomaly score is correctly computed."""
        expected, actual = load_outputs()
        assert approx_equal(actual['overall_anomaly_score'], expected['overall_anomaly_score']), \
            f"Overall score: expected {expected['overall_anomaly_score']}, got {actual['overall_anomaly_score']}"

    def test_scores_bounded(self):
        """Verify all anomaly scores are in [0, 1] range after clipping."""
        _, actual = load_outputs()
        for i, s in enumerate(actual['anomaly_scores']):
            assert 0.0 <= s <= 1.0, \
                f"Score[{i}] = {s} is outside [0, 1] range"


class TestSegmentResults:
    """Tests for per-segment anomaly detection results."""

    def test_segment_count(self):
        """Verify the correct number of segments are detected."""
        expected, actual = load_outputs()
        assert len(actual['segment_results']) == len(expected['segment_results']), \
            f"Expected {len(expected['segment_results'])} segments, got {len(actual['segment_results'])}"

    def test_segment_boundaries(self):
        """Verify segment start and end indices match expected values."""
        expected, actual = load_outputs()
        for i, (exp_seg, act_seg) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert act_seg['start'] == exp_seg['start'], \
                f"Segment {i} start: expected {exp_seg['start']}, got {act_seg['start']}"
            assert act_seg['end'] == exp_seg['end'], \
                f"Segment {i} end: expected {exp_seg['end']}, got {act_seg['end']}"

    def test_segment_thresholds(self):
        """Verify per-segment anomaly thresholds use segment-local statistics."""
        expected, actual = load_outputs()
        for i, (exp_seg, act_seg) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert approx_equal(act_seg['threshold'], exp_seg['threshold']), \
                f"Segment {i} threshold: expected {exp_seg['threshold']:.6f}, got {act_seg['threshold']:.6f}"

    def test_segment_mean_scores(self):
        """Verify per-segment mean anomaly scores are correctly averaged."""
        expected, actual = load_outputs()
        for i, (exp_seg, act_seg) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert approx_equal(act_seg['mean_score'], exp_seg['mean_score']), \
                f"Segment {i} mean_score: expected {exp_seg['mean_score']:.6f}, got {act_seg['mean_score']:.6f}"

    def test_segment_anomaly_counts(self):
        """Verify anomaly counts per segment match expected classification."""
        expected, actual = load_outputs()
        for i, (exp_seg, act_seg) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert act_seg['n_anomalies'] == exp_seg['n_anomalies'], \
                f"Segment {i} n_anomalies: expected {exp_seg['n_anomalies']}, got {act_seg['n_anomalies']}"

    def test_total_anomalies(self):
        """Verify total anomaly count across all segments."""
        expected, actual = load_outputs()
        assert actual['total_anomalies'] == expected['total_anomalies'], \
            f"Total anomalies: expected {expected['total_anomalies']}, got {actual['total_anomalies']}"


class TestSpectralDiagnostics:
    """Tests for spectral analysis diagnostic outputs."""

    def test_n_frequency_bins(self):
        """Verify the number of frequency bins matches series length / 2."""
        expected, actual = load_outputs()
        assert actual['spectral_diagnostics']['n_frequency_bins'] == \
               expected['spectral_diagnostics']['n_frequency_bins']

    def test_total_spectral_energy(self):
        """Verify total spectral energy computation with correct normalization."""
        expected, actual = load_outputs()
        exp_val = expected['spectral_diagnostics']['total_spectral_energy']
        act_val = actual['spectral_diagnostics']['total_spectral_energy']
        assert approx_equal(act_val, exp_val), \
            f"Total spectral energy: expected {exp_val}, got {act_val}"

    def test_envelope_energy(self):
        """Verify AR envelope total energy from fitted model."""
        expected, actual = load_outputs()
        exp_val = expected['spectral_diagnostics']['envelope_energy']
        act_val = actual['spectral_diagnostics']['envelope_energy']
        assert approx_equal(act_val, exp_val), \
            f"Envelope energy: expected {exp_val}, got {act_val}"

    def test_unexplained_ratio(self):
        """Verify unexplained spectral energy ratio computation."""
        expected, actual = load_outputs()
        exp_val = expected['spectral_diagnostics']['unexplained_ratio']
        act_val = actual['spectral_diagnostics']['unexplained_ratio']
        assert approx_equal(act_val, exp_val), \
            f"Unexplained ratio: expected {exp_val}, got {act_val}"

    def test_spectral_density_mean(self):
        """Verify mean spectral density across frequency bins."""
        expected, actual = load_outputs()
        exp_val = expected['spectral_diagnostics']['spectral_density_mean']
        act_val = actual['spectral_diagnostics']['spectral_density_mean']
        assert approx_equal(act_val, exp_val), \
            f"Spectral density mean: expected {exp_val}, got {act_val}"

    def test_n_effective(self):
        """Verify effective sample size accounts for window function."""
        expected, actual = load_outputs()
        assert actual['spectral_diagnostics']['n_effective'] == \
               expected['spectral_diagnostics']['n_effective'], \
            f"n_effective: expected {expected['spectral_diagnostics']['n_effective']}, got {actual['spectral_diagnostics']['n_effective']}"


class TestWhiteningDiagnostics:
    """Tests for whitening process diagnostics."""

    def test_whitened_variance(self):
        """Verify whitened series variance is correctly reported."""
        expected, actual = load_outputs()
        exp_val = expected['whitening_diagnostics']['whitened_variance']
        act_val = actual['whitening_diagnostics']['whitened_variance']
        assert approx_equal(act_val, exp_val), \
            f"Whitened variance: expected {exp_val}, got {act_val}"

    def test_whitened_mean(self):
        """Verify whitened series mean is approximately zero."""
        expected, actual = load_outputs()
        exp_val = expected['whitening_diagnostics']['whitened_mean']
        act_val = actual['whitening_diagnostics']['whitened_mean']
        assert approx_equal(act_val, exp_val, abs_tol=1e-4), \
            f"Whitened mean: expected {exp_val}, got {act_val}"


class TestParameters:
    """Tests for pipeline parameter reporting."""

    def test_parameters_match(self):
        """Verify all pipeline parameters are correctly reported."""
        expected, actual = load_outputs()
        for key in expected['parameters']:
            assert actual['parameters'][key] == expected['parameters'][key], \
                f"Parameter '{key}': expected {expected['parameters'][key]}, got {actual['parameters'].get(key)}"
