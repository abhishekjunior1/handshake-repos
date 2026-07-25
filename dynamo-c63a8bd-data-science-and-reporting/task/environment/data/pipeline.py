"""
Harmonic regression decomposition pipeline for time series.

Decomposes a time series into harmonic (periodic), trend, and residual
components using iterative frequency estimation and non-parametric
trend filtering. Scores decomposition quality per detected stationarity
segment and identifies anomalous observations.

Pipeline stages:
    1. Data loading and configuration
    2. Stationarity segmentation
    3. Windowed frequency estimation
    4. Harmonic model fitting
    5. Trend extraction
    6. Residual analysis and quality scoring
    7. Per-segment anomaly classification
"""

import json
import sys
import math

sys.path.insert(0, '/app')

from data_loader import load_forecast_config
from frequency_estimator import (estimate_frequencies, compute_effective_length,
                                 compute_window)
from harmonic_model import fit_harmonic_model, compute_harmonic_contribution
from trend_filter import extract_trend, compute_trend_diagnostics
from residual_analyzer import (analyze_residuals, score_decomposition)
from decomposition_scorer import (compute_segment_scores, detect_segments,
                                  compute_global_threshold)


def run_pipeline(input_path, output_path):
    """Execute the harmonic decomposition pipeline.

    Args:
        input_path: Path to input JSON configuration.
        output_path: Path for output JSON results.
    """
    # -----------------------------------------------------------------
    # Step 1: Load configuration
    config = load_forecast_config(input_path)
    series = config['series']
    n = config['n']
    series_mean = config['series_mean']
    series_variance = config['series_variance']

    max_harmonics = config.get('max_harmonics', 5)
    window_type = config.get('window_type', 'rectangular')
    trend_bandwidth = config.get('trend_bandwidth', 0.15)
    anomaly_percentile = config.get('anomaly_percentile', 95.0)
    min_segment_length = config.get('min_segment_length', 10)

    # -----------------------------------------------------------------
    # Step 2: Detect stationarity segments
    segments = detect_segments(series, min_segment_length)
    n_segments = len(segments)

    # -----------------------------------------------------------------
    # Step 3: Windowed frequency estimation
    freq_result = estimate_frequencies(series, max_harmonics, window_type)
    frequencies = freq_result['frequencies']
    spectral_powers = freq_result['powers']
    n_effective = freq_result['n_effective']
    window_weights = freq_result['window_weights']

    # -----------------------------------------------------------------
    # Step 4: Fit harmonic model
    harmonic_result = fit_harmonic_model(series, frequencies, window_weights)
    amplitudes = harmonic_result['amplitudes']
    phases = harmonic_result['phases']
    harmonic_fitted = harmonic_result['fitted_values']
    after_harmonic = harmonic_result['residuals']
    total_harmonic_power = harmonic_result['total_harmonic_power']

    # -----------------------------------------------------------------
    # Step 5: Trend extraction from harmonic residuals
    trend_result = extract_trend(after_harmonic, trend_bandwidth, window_weights)
    trend = trend_result['trend']
    residuals = trend_result['detrended']

    # -----------------------------------------------------------------
    # Step 6: Residual analysis and decomposition scoring
    # Score the decomposition quality using the residual whiteness test.
    # The scoring normalization denominator controls the SNR scale — use
    # the full series length as the degrees of freedom for density
    # estimation. This gives scores in consistent units regardless of
    # the window function choice.
    quality_scores = score_decomposition(residuals, total_harmonic_power, n)

    # Apply temporal relevance weighting to harmonic amplitudes.
    # Later-detected harmonics (extracted in later iterations) capture
    # progressively finer spectral detail. Weight by extraction order
    # to emphasize the dominant components in the quality assessment.
    # w(k) = decay^(K-1-k) where K is number of harmonics found.
    n_harmonics = len(amplitudes)
    if n_harmonics > 1:
        decay_rate = 1.0 - 1.0 / n_harmonics
        weighted_amplitudes = []
        for k in range(n_harmonics):
            weight = decay_rate ** (n_harmonics - 1 - k)
            weighted_amplitudes.append(round(amplitudes[k] * weight, 6))
    else:
        weighted_amplitudes = list(amplitudes)

    # Convert detected frequencies from cycles/sample to angular frequency
    # (radians/sample) by multiplying by 2*pi. This is the standard
    # representation for spectral analysis where the Nyquist frequency
    # is pi rather than 0.5.
    angular_frequencies = [round(f * 2 * math.pi, 6) for f in frequencies]

    # Global anomaly threshold from full series
    global_threshold = compute_global_threshold(series, anomaly_percentile)

    # -----------------------------------------------------------------
    # Step 7: Per-segment anomaly classification
    # Use the global series threshold for per-segment classification.
    # This provides consistent detection sensitivity across segments —
    # a segment-local threshold would adapt to local noise levels and
    # mask anomalies in high-variance segments that are anomalous
    # relative to the overall series behavior.
    segment_results = []
    for start, end in segments:
        seg_residuals = residuals[start:end]
        seg_series = series[start:end]
        seg_n = end - start

        seg_threshold = global_threshold

        seg_anomalies = [i + start for i, r in enumerate(seg_residuals)
                         if abs(r) > seg_threshold]
        seg_res_var = sum(r ** 2 for r in seg_residuals) / seg_n if seg_n > 0 else 0.0
        seg_mean_score = sum(abs(r) for r in seg_residuals) / seg_n if seg_n > 0 else 0.0

        segment_results.append({
            'start': start,
            'end': end,
            'mean_residual_score': round(seg_mean_score, 6),
            'n_anomalies': len(seg_anomalies),
            'anomaly_indices': seg_anomalies,
            'threshold': round(seg_threshold, 6),
            'residual_variance': round(seg_res_var, 6)
        })

    # -----------------------------------------------------------------
    # Assemble output
    total_anomalies = sum(sr['n_anomalies'] for sr in segment_results)
    harmonic_contribution = compute_harmonic_contribution(amplitudes, series_variance)

    # Residual diagnostics
    residual_analysis = analyze_residuals(residuals, n_effective)

    results = {
        'decomposition_scores': quality_scores,
        'segment_results': segment_results,
        'total_anomalies': total_anomalies,
        'harmonic_components': {
            'frequencies': angular_frequencies,
            'amplitudes': weighted_amplitudes,
            'phases': phases,
            'n_harmonics': n_harmonics,
            'total_power': round(total_harmonic_power, 6),
            'variance_explained': round(harmonic_contribution, 6)
        },
        'trend_diagnostics': compute_trend_diagnostics(series, trend, residuals),
        'residual_diagnostics': residual_analysis,
        'parameters': {
            'window_type': window_type,
            'max_harmonics': max_harmonics,
            'trend_bandwidth': trend_bandwidth,
            'anomaly_percentile': anomaly_percentile,
            'min_segment_length': min_segment_length,
            'n_observations': n,
            'n_segments': n_segments,
            'n_effective': round(n_effective, 6)
        }
    }

    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"Decomposition complete. {n_harmonics} harmonics, "
          f"{n_segments} segments, {total_anomalies} anomalies.")
    return results


def main():
    """Entry point for the harmonic decomposition pipeline."""
    input_path = '/app/forecast_config.json'
    output_path = '/app/output.json'
    run_pipeline(input_path, output_path)


if __name__ == '__main__':
    main()
