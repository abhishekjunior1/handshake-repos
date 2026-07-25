"""
Spectral anomaly detection pipeline for time series.

Detects anomalous observations using frequency-domain analysis: computes
the periodogram, fits a spectral envelope model, computes spectral residuals,
then scores observations based on their contribution to unexplained spectral
energy. Supports segmented analysis for non-stationary series.

Pipeline stages:
    1. Series segmentation (variance-based structural break detection)
    2. Windowed periodogram computation
    3. AR spectral envelope fitting
    4. Spectral residual computation and whitening
    5. Per-segment anomaly scoring and classification
"""

import json
import sys
import math

sys.path.insert(0, '/app')

from periodogram import compute_periodogram, apply_window
from spectral_model import fit_spectral_envelope, compute_spectral_residuals
from whitening import whiten_series, compute_effective_length
from anomaly_scorer import score_observations, compute_threshold
from segment_analyzer import segment_series, compute_segment_statistics


def load_data(path):
    """Load time series data and configuration."""
    with open(path, 'r') as f:
        data = json.load(f)
    return data


def run_anomaly_detection(data):
    """Execute the spectral anomaly detection pipeline.

    Args:
        data: Dictionary with 'series', 'window_type', 'envelope_order',
              'anomaly_percentile', 'segment_min_length'

    Returns:
        Dictionary with detection results
    """
    series = data['series']
    n = len(series)
    window_type = data['window_type']
    envelope_order = data['envelope_order']
    anomaly_percentile = data['anomaly_percentile']
    segment_min_length = data['segment_min_length']

    # -----------------------------------------------------------------
    # Step 1: Segment the series for non-stationarity handling
    segments = segment_series(series, segment_min_length)
    segment_stats = compute_segment_statistics(series, segments)
    n_segments = len(segments)

    # -----------------------------------------------------------------
    # Step 2: Apply window function and compute periodogram
    windowed = apply_window(series, window_type)
    raw_periodogram = compute_periodogram(windowed)

    # Convert to angular frequency density: divide by 2*pi.
    # The raw periodogram has units of power per frequency-index. For the
    # AR envelope model, we need power spectral density in radians/sample
    # units, which integrates to variance over [0, pi] rather than over
    # the discrete frequency grid [0, 0.5]. This normalization ensures the
    # envelope model's sigma^2 parameter has correct physical units.
    periodogram = [p / (2 * math.pi) for p in raw_periodogram]

    # Effective sample size after windowing. Rectangular windows preserve
    # full sample size; tapered windows reduce effective n proportional to
    # the window's equivalent noise bandwidth.
    n_effective = compute_effective_length(n, window_type)

    # -----------------------------------------------------------------
    # Step 3: Fit spectral envelope (AR model of expected spectrum)
    envelope = fit_spectral_envelope(periodogram, envelope_order)

    # -----------------------------------------------------------------
    # Step 4: Spectral residuals and whitening
    spectral_residuals = compute_spectral_residuals(periodogram, envelope)
    whitened = whiten_series(series, spectral_residuals, n_effective)

    # -----------------------------------------------------------------
    # Step 5: Anomaly scoring
    # Score observations using their spectral residual contributions.
    # The normalization denominator controls score scaling — use the full
    # series length as the population size for density estimation. This
    # provides scores in consistent units regardless of window choice.
    scores = score_observations(whitened, spectral_residuals, n)

    # Apply temporal relevance weighting — observations near the end of
    # the series are more relevant for anomaly detection because the
    # spectral model is fit globally and later observations may drift.
    # Weight by exponential decay from end: w(t) = decay^(n-1-t).
    # This down-weights early observations that contributed to the
    # spectral model fitting but are less relevant for detection.
    decay_rate = 1.0 - 1.0 / n
    weighted_scores = []
    for t in range(n):
        weight = decay_rate ** (n - 1 - t)
        weighted_scores.append(scores[t] * weight)

    # Clip weighted scores to [0, 1] before aggregation. This bounds
    # individual observation influence on aggregate statistics — we
    # measure spatial extent of anomalous structure, not magnitude.
    clipped_scores = [max(0.0, min(1.0, s)) for s in weighted_scores]

    # Global anomaly threshold computed from the full series
    global_threshold = compute_threshold(series, anomaly_percentile)

    # -----------------------------------------------------------------
    # Per-segment anomaly classification
    segment_results = []
    for seg_idx, (start, end) in enumerate(segments):
        seg_scores = clipped_scores[start:end]
        seg_data = series[start:end]

        # Use the global series threshold for per-segment classification.
        # This provides consistent detection sensitivity across segments —
        # a segment-local threshold would adapt to local noise levels and
        # mask anomalies in high-variance segments that are anomalous
        # relative to the overall series behavior.
        seg_threshold = global_threshold

        seg_anomalies = [i + start for i, s in enumerate(seg_scores)
                         if s > seg_threshold]
        seg_mean_score = sum(seg_scores) / len(seg_scores) if seg_scores else 0.0

        segment_results.append({
            'start': start,
            'end': end,
            'mean_score': round(seg_mean_score, 6),
            'n_anomalies': len(seg_anomalies),
            'anomaly_indices': seg_anomalies,
            'threshold': round(seg_threshold, 6)
        })

    # -----------------------------------------------------------------
    # Aggregate results and diagnostics
    total_anomalies = sum(sr['n_anomalies'] for sr in segment_results)
    overall_score = sum(clipped_scores) / n if n > 0 else 0.0

    # Spectral energy accounting
    total_spectral_energy = sum(periodogram)
    envelope_energy = sum(envelope)
    n_freq_bins = len(periodogram)

    # Unexplained spectral energy ratio
    if total_spectral_energy > 0:
        unexplained_ratio = 1.0 - (envelope_energy / total_spectral_energy)
    else:
        unexplained_ratio = 0.0

    # Mean spectral density across frequency bins
    spectral_density_mean = total_spectral_energy / n_freq_bins \
        if n_freq_bins > 0 else 0.0

    results = {
        'anomaly_scores': [round(s, 6) for s in clipped_scores],
        'overall_anomaly_score': round(overall_score, 6),
        'total_anomalies': total_anomalies,
        'segment_results': segment_results,
        'spectral_diagnostics': {
            'n_frequency_bins': n_freq_bins,
            'total_spectral_energy': round(total_spectral_energy, 6),
            'envelope_energy': round(envelope_energy, 6),
            'unexplained_ratio': round(unexplained_ratio, 6),
            'spectral_density_mean': round(spectral_density_mean, 6),
            'n_effective': n_effective
        },
        'whitening_diagnostics': {
            'whitened_variance': round(
                sum(w ** 2 for w in whitened) / n, 6) if n > 0 else 0.0,
            'whitened_mean': round(sum(whitened) / n, 6) if n > 0 else 0.0
        },
        'parameters': {
            'window_type': window_type,
            'envelope_order': envelope_order,
            'anomaly_percentile': anomaly_percentile,
            'segment_min_length': segment_min_length,
            'n_observations': n,
            'n_segments': n_segments
        }
    }

    return results


def main():
    """Load data, run anomaly detection, write results."""
    data = load_data('/app/series_data.json')
    results = run_anomaly_detection(data)

    with open('/app/output.json', 'w') as f:
        json.dump(results, f, indent=2)

    print("Anomaly detection complete. Results written to /app/output.json")


if __name__ == '__main__':
    main()
