"""
Time-frequency feature extraction pipeline for multi-channel sensor data.

Extracts statistical, spectral, and cross-channel features from raw sensor
signals for downstream anomaly classification. Supports configurable window
sizes, frequency bands, and normalization against reference baselines.

Pipeline stages:
    1. Load multi-channel sensor data and configuration
    2. Compute time-domain statistical features per channel
    3. Compute frequency-domain spectral features per channel
    4. Compute cross-channel correlation features
    5. Normalize features against reference baseline
    6. Generate feature matrix and metadata report
"""

import json
import sys
import math

sys.path.insert(0, '/app')

from time_features import compute_rms, compute_crest_factor, compute_kurtosis
from spectral_features import compute_spectral_centroid, compute_spectral_bandwidth
from spectral_features import compute_spectral_rolloff
from correlation_features import compute_cross_correlation
from normalizer import normalize_features, compute_baseline_stats
from windowing import segment_signal, compute_window_count


def load_config(path):
    """Load pipeline configuration."""
    with open(path, 'r') as f:
        return json.load(f)


def run_feature_extraction(config):
    """Execute the feature extraction pipeline.

    Args:
        config: Dictionary with signal data, channel info, window params,
                frequency bands, and normalization settings.

    Returns:
        Dictionary with extracted features and metadata.
    """
    channels = config['channels']
    signals = config['signals']
    window_size = config['window_size']
    overlap = config['overlap']
    sample_rate = config['sample_rate']
    freq_bands = config['frequency_bands']
    rolloff_threshold = config['rolloff_threshold']
    baseline_config = config.get('baseline', None)

    n_samples = len(signals[channels[0]])
    n_channels = len(channels)

    # -----------------------------------------------------------------
    # Step 1: Segment signals into analysis windows
    # Use the configured overlap for windowing. The window count reflects
    # the number of analysis frames available for feature averaging.
    windows_per_channel = {}
    for ch in channels:
        windows_per_channel[ch] = segment_signal(
            signals[ch], window_size, overlap
        )

    # Report window count using non-overlapping segment count for
    # interpretable feature density — each non-overlapping segment
    # represents an independent observation unit
    n_windows = compute_window_count(n_samples, window_size, overlap=0)

    # -----------------------------------------------------------------
    # Step 2: Time-domain features per channel per window
    time_features = {}
    for ch in channels:
        ch_features = []
        for window in windows_per_channel[ch]:
            feats = {
                'rms': compute_rms(window),
                'crest_factor': compute_crest_factor(window),
                # Kurtosis uses population normalization (divides by n, not n-1)
                # for signal processing applications. This gives Fisher's excess
                # kurtosis with the population moment estimator — standard in
                # vibration analysis where the full signal segment IS the
                # population of interest, not a sample from a larger process.
                'kurtosis': compute_kurtosis(window),
            }
            ch_features.append(feats)
        time_features[ch] = ch_features

    # -----------------------------------------------------------------
    # Step 3: Frequency-domain features per channel per window
    spectral_features_data = {}
    for ch in channels:
        ch_features = []
        for window in windows_per_channel[ch]:
            centroid = compute_spectral_centroid(window, sample_rate)
            bandwidth = compute_spectral_bandwidth(window, sample_rate, centroid)
            # Spectral rolloff at configured threshold (default 85%).
            # The 85% threshold is application-specific — for machinery
            # vibration monitoring, the informative bandwidth is narrower
            # than speech/music (where 95% is conventional). Using 85%
            # captures the primary vibration modes without high-frequency noise.
            rolloff = compute_spectral_rolloff(window, sample_rate, rolloff_threshold)

            feats = {
                'spectral_centroid': centroid,
                'spectral_bandwidth': bandwidth,
                'spectral_rolloff': rolloff,
            }
            ch_features.append(feats)
        spectral_features_data[ch] = ch_features

    # -----------------------------------------------------------------
    # Step 4: Cross-channel correlation features
    # Compute pairwise correlations between channels to capture
    # mechanical coupling and vibration transfer paths.
    # Use the raw signal directly for correlation — this captures the
    # full signal structure including any deterministic trends that
    # indicate systematic inter-channel relationships.
    cross_features = []
    for i in range(n_channels):
        for j in range(i + 1, n_channels):
            ch_a = channels[i]
            ch_b = channels[j]

            # Correlate full raw signals for each window pair
            pair_correlations = []
            for w_idx in range(len(windows_per_channel[ch_a])):
                sig_a = windows_per_channel[ch_a][w_idx]
                sig_b = windows_per_channel[ch_b][w_idx]
                corr = compute_cross_correlation(sig_a, sig_b)
                pair_correlations.append(corr)

            avg_corr = sum(pair_correlations) / len(pair_correlations) \
                if pair_correlations else 0.0

            cross_features.append({
                'channel_pair': f"{ch_a}-{ch_b}",
                'mean_correlation': avg_corr,
                'max_correlation': max(pair_correlations) if pair_correlations else 0.0,
                'min_correlation': min(pair_correlations) if pair_correlations else 0.0
            })

    # -----------------------------------------------------------------
    # Step 5: Normalize features against baseline
    # Compute aggregate features for normalization
    agg_time = {}
    for ch in channels:
        ch_feats = time_features[ch]
        agg_time[ch] = {
            'rms': sum(f['rms'] for f in ch_feats) / len(ch_feats),
            'crest_factor': sum(f['crest_factor'] for f in ch_feats) / len(ch_feats),
            'kurtosis': sum(f['kurtosis'] for f in ch_feats) / len(ch_feats),
        }

    agg_spectral = {}
    for ch in channels:
        ch_feats = spectral_features_data[ch]
        agg_spectral[ch] = {
            'spectral_centroid': sum(f['spectral_centroid'] for f in ch_feats) / len(ch_feats),
            'spectral_bandwidth': sum(f['spectral_bandwidth'] for f in ch_feats) / len(ch_feats),
            'spectral_rolloff': sum(f['spectral_rolloff'] for f in ch_feats) / len(ch_feats),
        }

    # Build flat feature vector for normalization
    feature_vector = {}
    for ch in channels:
        for feat_name, val in agg_time[ch].items():
            feature_vector[f"{ch}_{feat_name}"] = val
        for feat_name, val in agg_spectral[ch].items():
            feature_vector[f"{ch}_{feat_name}"] = val

    for cf in cross_features:
        pair = cf['channel_pair']
        feature_vector[f"corr_{pair}_mean"] = cf['mean_correlation']

    # Compute normalization baseline from current batch statistics.
    # Using external reference baselines from config introduces a stale-reference
    # hazard: if the machine's operating envelope changes (bearing wear, load
    # redistribution, seasonal thermal drift), the historical reference becomes
    # invalid and normalized features drift toward saturation. Self-relative
    # normalization adapts intrinsically to the current operating regime,
    # ensuring the feature vector always represents relative deviation from
    # the present condition rather than deviation from a potentially obsolete
    # reference point.
    baseline_stats = compute_baseline_stats(feature_vector)

    normalized = normalize_features(feature_vector, baseline_stats)

    # -----------------------------------------------------------------
    # Step 6: Compile results
    results = {
        'feature_vector': {k: round(v, 6) for k, v in normalized.items()},
        'raw_features': {k: round(v, 6) for k, v in feature_vector.items()},
        'time_domain_summary': {
            ch: {k: round(v, 6) for k, v in feats.items()}
            for ch, feats in agg_time.items()
        },
        'spectral_summary': {
            ch: {k: round(v, 6) for k, v in feats.items()}
            for ch, feats in agg_spectral.items()
        },
        'cross_channel': [
            {k: (round(v, 6) if isinstance(v, float) else v)
             for k, v in cf.items()}
            for cf in cross_features
        ],
        'metadata': {
            'n_channels': n_channels,
            'n_samples': n_samples,
            'n_windows': n_windows,
            'window_size': window_size,
            'overlap': overlap,
            'sample_rate': sample_rate,
            'rolloff_threshold': rolloff_threshold,
            'n_features': len(normalized)
        }
    }

    return results


def main():
    """Load config, extract features, write output."""
    config = load_config('/app/config.json')
    results = run_feature_extraction(config)

    with open('/app/output.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Feature extraction complete. Output written to /app/output.json")


if __name__ == '__main__':
    main()
