"""Tests for the time-frequency feature extraction pipeline.

Validates that the pipeline correctly computes time-domain features,
spectral features, cross-channel correlations on detrended signals,
normalizes against the reference baseline, and reports correct window counts.
"""

import json

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


class TestFeatureVector:
    """Tests for the normalized feature vector output."""

    def test_feature_count(self):
        """Verify the correct number of features are extracted."""
        expected, actual = load_outputs()
        assert len(actual['feature_vector']) == len(expected['feature_vector']), \
            f"Feature count: expected {len(expected['feature_vector'])}, got {len(actual['feature_vector'])}"

    def test_feature_values(self):
        """Verify normalized feature values match expected output."""
        expected, actual = load_outputs()
        for key in expected['feature_vector']:
            exp_val = expected['feature_vector'][key]
            act_val = actual['feature_vector'].get(key)
            assert act_val is not None, f"Missing feature: {key}"
            assert approx_equal(act_val, exp_val), \
                f"Feature '{key}': expected {exp_val:.6f}, got {act_val:.6f}"

    def test_feature_keys_match(self):
        """Verify feature names match expected set."""
        expected, actual = load_outputs()
        exp_keys = set(expected['feature_vector'].keys())
        act_keys = set(actual['feature_vector'].keys())
        assert act_keys == exp_keys, \
            f"Feature key mismatch. Extra: {act_keys - exp_keys}, Missing: {exp_keys - act_keys}"


class TestRawFeatures:
    """Tests for raw (pre-normalization) feature values."""

    def test_raw_feature_values(self):
        """Verify raw features are correctly computed before normalization."""
        expected, actual = load_outputs()
        for key in expected['raw_features']:
            exp_val = expected['raw_features'][key]
            act_val = actual['raw_features'].get(key)
            assert act_val is not None, f"Missing raw feature: {key}"
            assert approx_equal(act_val, exp_val), \
                f"Raw feature '{key}': expected {exp_val:.6f}, got {act_val:.6f}"


class TestCrossChannel:
    """Tests for cross-channel correlation features."""

    def test_correlation_count(self):
        """Verify correct number of channel pairs are computed."""
        expected, actual = load_outputs()
        assert len(actual['cross_channel']) == len(expected['cross_channel']), \
            f"Cross-channel pairs: expected {len(expected['cross_channel'])}, got {len(actual['cross_channel'])}"

    def test_correlation_values(self):
        """Verify cross-channel correlations use detrended signals."""
        expected, actual = load_outputs()
        for i, (exp_cf, act_cf) in enumerate(zip(expected['cross_channel'], actual['cross_channel'])):
            assert act_cf['channel_pair'] == exp_cf['channel_pair'], \
                f"Pair {i} name mismatch"
            for key in ['mean_correlation', 'max_correlation', 'min_correlation']:
                assert approx_equal(act_cf[key], exp_cf[key]), \
                    f"Pair {i} '{key}': expected {exp_cf[key]:.6f}, got {act_cf[key]:.6f}"


class TestTimeDomain:
    """Tests for time-domain feature summary."""

    def test_time_features(self):
        """Verify time-domain features per channel are correct."""
        expected, actual = load_outputs()
        for ch in expected['time_domain_summary']:
            for feat in expected['time_domain_summary'][ch]:
                exp_val = expected['time_domain_summary'][ch][feat]
                act_val = actual['time_domain_summary'].get(ch, {}).get(feat)
                assert act_val is not None, f"Missing time feature {ch}/{feat}"
                assert approx_equal(act_val, exp_val), \
                    f"Time feature {ch}/{feat}: expected {exp_val:.6f}, got {act_val:.6f}"


class TestSpectral:
    """Tests for spectral feature summary."""

    def test_spectral_features(self):
        """Verify spectral features per channel are correct."""
        expected, actual = load_outputs()
        for ch in expected['spectral_summary']:
            for feat in expected['spectral_summary'][ch]:
                exp_val = expected['spectral_summary'][ch][feat]
                act_val = actual['spectral_summary'].get(ch, {}).get(feat)
                assert act_val is not None, f"Missing spectral feature {ch}/{feat}"
                assert approx_equal(act_val, exp_val), \
                    f"Spectral feature {ch}/{feat}: expected {exp_val:.6f}, got {act_val:.6f}"


class TestMetadata:
    """Tests for pipeline metadata reporting."""

    def test_window_count(self):
        """Verify reported window count matches actual overlapping segmentation."""
        expected, actual = load_outputs()
        assert actual['metadata']['n_windows'] == expected['metadata']['n_windows'], \
            f"n_windows: expected {expected['metadata']['n_windows']}, got {actual['metadata']['n_windows']}"

    def test_parameters(self):
        """Verify pipeline parameters are correctly reported."""
        expected, actual = load_outputs()
        for key in ['n_channels', 'n_samples', 'window_size', 'overlap',
                    'sample_rate', 'rolloff_threshold', 'n_features']:
            assert actual['metadata'][key] == expected['metadata'][key], \
                f"Metadata '{key}': expected {expected['metadata'][key]}, got {actual['metadata'][key]}"
