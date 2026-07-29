"""Tests for the harmonic regression decomposition pipeline.

Validates that the pipeline correctly estimates frequencies, fits harmonics,
extracts trends, scores decomposition quality, and classifies per-segment
anomalies with appropriate thresholds.
"""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PATH = os.path.join(TESTS_DIR, 'expected_output.json')
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


class TestDecompositionScores:
    """Tests for decomposition quality scoring."""

    def test_snr_score(self):
        """Verify signal-to-noise ratio uses correct effective sample size."""
        expected, actual = load_outputs()
        assert approx_equal(actual['decomposition_scores']['snr_score'],
                           expected['decomposition_scores']['snr_score']), \
            f"SNR: expected {expected['decomposition_scores']['snr_score']}, got {actual['decomposition_scores']['snr_score']}"

    def test_whiteness_score(self):
        """Verify residual whiteness assessment."""
        expected, actual = load_outputs()
        assert approx_equal(actual['decomposition_scores']['whiteness_score'],
                           expected['decomposition_scores']['whiteness_score']), \
            f"Whiteness: expected {expected['decomposition_scores']['whiteness_score']}, got {actual['decomposition_scores']['whiteness_score']}"

    def test_overall_quality(self):
        """Verify combined decomposition quality metric."""
        expected, actual = load_outputs()
        assert approx_equal(actual['decomposition_scores']['overall_quality'],
                           expected['decomposition_scores']['overall_quality']), \
            f"Quality: expected {expected['decomposition_scores']['overall_quality']}, got {actual['decomposition_scores']['overall_quality']}"


class TestSegmentResults:
    """Tests for per-segment anomaly classification."""

    def test_segment_count(self):
        """Verify correct number of segments detected."""
        expected, actual = load_outputs()
        assert len(actual['segment_results']) == len(expected['segment_results']), \
            f"Segments: expected {len(expected['segment_results'])}, got {len(actual['segment_results'])}"

    def test_segment_thresholds(self):
        """Verify per-segment anomaly thresholds use correct scope."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert approx_equal(act['threshold'], exp['threshold']), \
                f"Segment {i} threshold: expected {exp['threshold']}, got {act['threshold']}"

    def test_segment_anomaly_counts(self):
        """Verify anomaly detection counts per segment."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert act['n_anomalies'] == exp['n_anomalies'], \
                f"Segment {i} anomalies: expected {exp['n_anomalies']}, got {act['n_anomalies']}"

    def test_segment_boundaries(self):
        """Verify segment start/end positions."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['segment_results'], actual['segment_results'])):
            assert act['start'] == exp['start'] and act['end'] == exp['end'], \
                f"Segment {i}: expected [{exp['start']},{exp['end']}), got [{act['start']},{act['end']})"

    def test_total_anomalies(self):
        """Verify total anomaly count across all segments."""
        expected, actual = load_outputs()
        assert actual['total_anomalies'] == expected['total_anomalies'], \
            f"Total anomalies: expected {expected['total_anomalies']}, got {actual['total_anomalies']}"


class TestHarmonicComponents:
    """Tests for harmonic extraction results."""

    def test_frequencies(self):
        """Verify detected angular frequencies match expected."""
        expected, actual = load_outputs()
        assert len(actual['harmonic_components']['frequencies']) == len(expected['harmonic_components']['frequencies']), \
            f"N frequencies: expected {len(expected['harmonic_components']['frequencies'])}, got {len(actual['harmonic_components']['frequencies'])}"
        for i, (exp, act) in enumerate(zip(expected['harmonic_components']['frequencies'],
                                            actual['harmonic_components']['frequencies'])):
            assert approx_equal(act, exp), \
                f"Frequency {i}: expected {exp}, got {act}"

    def test_amplitudes(self):
        """Verify weighted harmonic amplitudes."""
        expected, actual = load_outputs()
        for i, (exp, act) in enumerate(zip(expected['harmonic_components']['amplitudes'],
                                            actual['harmonic_components']['amplitudes'])):
            assert approx_equal(act, exp), \
                f"Amplitude {i}: expected {exp}, got {act}"

    def test_total_power(self):
        """Verify total harmonic power computation."""
        expected, actual = load_outputs()
        assert approx_equal(actual['harmonic_components']['total_power'],
                           expected['harmonic_components']['total_power']), \
            f"Power: expected {expected['harmonic_components']['total_power']}, got {actual['harmonic_components']['total_power']}"

    def test_variance_explained(self):
        """Verify harmonic variance explanation fraction."""
        expected, actual = load_outputs()
        assert approx_equal(actual['harmonic_components']['variance_explained'],
                           expected['harmonic_components']['variance_explained']), \
            f"Var explained: expected {expected['harmonic_components']['variance_explained']}, got {actual['harmonic_components']['variance_explained']}"


class TestParameters:
    """Tests for parameter reporting."""

    def test_n_effective(self):
        """Verify effective sample size correctly reported."""
        expected, actual = load_outputs()
        assert approx_equal(actual['parameters']['n_effective'],
                           expected['parameters']['n_effective']), \
            f"n_effective: expected {expected['parameters']['n_effective']}, got {actual['parameters']['n_effective']}"

    def test_n_segments(self):
        """Verify segment count parameter."""
        expected, actual = load_outputs()
        assert actual['parameters']['n_segments'] == expected['parameters']['n_segments']

    def test_window_type(self):
        """Verify window type parameter preserved."""
        expected, actual = load_outputs()
        assert actual['parameters']['window_type'] == expected['parameters']['window_type']


class TestResidualDiagnostics:
    """Tests for residual analysis outputs."""

    def test_residual_variance(self):
        """Verify residual variance computation."""
        expected, actual = load_outputs()
        assert approx_equal(actual['residual_diagnostics']['residual_variance'],
                           expected['residual_diagnostics']['residual_variance']), \
            f"Res var: expected {expected['residual_diagnostics']['residual_variance']}, got {actual['residual_diagnostics']['residual_variance']}"

    def test_ljung_box(self):
        """Verify Ljung-Box portmanteau test statistic."""
        expected, actual = load_outputs()
        assert approx_equal(actual['residual_diagnostics']['ljung_box_statistic'],
                           expected['residual_diagnostics']['ljung_box_statistic']), \
            f"LB stat: expected {expected['residual_diagnostics']['ljung_box_statistic']}, got {actual['residual_diagnostics']['ljung_box_statistic']}"
