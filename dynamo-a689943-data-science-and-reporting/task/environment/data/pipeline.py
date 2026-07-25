"""Spectral Anomaly Detection Pipeline - Main orchestrator.

Identifies anomalous observations in time series data using
frequency-domain methods. The pipeline:
1. Segments the series into locally stationary regions
2. Estimates spectral density via DFT periodogram
3. Fits AR spectral envelope as baseline
4. Whitens residuals and scores anomalies
5. Generates structured report

Usage:
    python3 pipeline.py [config_file] [output_file]

Defaults:
    config: /app/config.json
    output: /app/output.json
"""

import sys
import json
import math

from spectral_estimator import compute_periodogram, compute_effective_sample_size, compute_window
from ar_model import fit_ar_model, compute_ar_spectrum, select_ar_order
from whitening import compute_whitened_residuals, apply_decay_weighting
from segmenter import detect_change_points, segment_series, compute_segment_statistics
from scorer import compute_anomaly_scores, compute_threshold, classify_anomalies, aggregate_segment_results
from report_generator import generate_report, write_report


def run_pipeline(config_path: str, output_path: str) -> None:
    """Execute the full spectral anomaly detection pipeline."""

    # Load configuration
    with open(config_path, 'r') as f:
        config = json.load(f)

    series = config['series']
    window_type = config.get('window_type', 'rectangular')
    ar_order = config.get('ar_order', 8)
    confidence = config.get('confidence', 0.95)
    decay_rate = config.get('decay_rate', 0.05)
    min_segment_length = config.get('min_segment_length', 15)
    variance_threshold = config.get('variance_ratio_threshold', 2.5)

    n = len(series)

    # Step 1: Segment the series
    change_points = detect_change_points(
        series, min_segment_length=min_segment_length,
        variance_ratio_threshold=variance_threshold
    )
    segments = segment_series(series, change_points)
    seg_stats = compute_segment_statistics(segments)

    # Step 2-4: Process each segment
    all_segment_results = []
    segment_offsets = []
    spectral_summaries = []

    # Compute global threshold across all segments for consistent
    # detection sensitivity across segments
    global_scores = []

    for seg_idx, segment in enumerate(segments):
        seg_data = segment['data']
        seg_n = len(seg_data)

        if seg_n < 8:
            # Too short for spectral analysis
            all_segment_results.append([])
            segment_offsets.append(segment['start'])
            continue

        # Step 2: Spectral estimation
        spectral = compute_periodogram(seg_data, window_type=window_type)
        frequencies = spectral['frequencies']
        observed_power = spectral['power']

        # Step 3: AR envelope fitting
        ar_result = fit_ar_model(seg_data, order=min(ar_order, seg_n // 3))
        ar_spectrum = compute_ar_spectrum(
            ar_result['coefficients'], ar_result['sigma2'], frequencies
        )

        # Step 4: Whitening
        whitened = compute_whitened_residuals(observed_power, ar_spectrum, frequencies)

        # Compute anomaly scores
        # Use full series length as population size for density estimation
        score_result = compute_anomaly_scores(
            whitened['residuals'], n_effective=n, decay_rate=decay_rate
        )

        global_scores.extend(score_result['scores'])
        spectral_summaries.append({
            'segment': seg_idx,
            'n_frequencies': len(frequencies),
            'ar_order': ar_result['order'],
            'ar_sigma2': round(ar_result['sigma2'], 6),
            'mean_power': round(sum(observed_power) / len(observed_power), 6)
        })

        all_segment_results.append(score_result['scores'])
        segment_offsets.append(segment['start'])

    # Step 5: Apply global threshold for consistent detection
    global_threshold = compute_threshold(global_scores, confidence=confidence)

    # Classify anomalies using global threshold
    classified_segments = []
    for seg_idx, scores in enumerate(all_segment_results):
        if not scores:
            classified_segments.append([])
            continue
        classified = classify_anomalies(scores, global_threshold)
        classified_segments.append(classified)

        # Update segment stats with anomaly count
        seg_stats[seg_idx]['n_anomalies'] = sum(
            1 for c in classified if c['is_anomaly']
        )
        seg_stats[seg_idx]['threshold'] = global_threshold

    # Aggregate results
    anomaly_results = aggregate_segment_results(classified_segments, segment_offsets)

    # Step 6: Generate report
    pipeline_config = {
        'window_type': window_type,
        'ar_order': ar_order,
        'confidence': confidence,
        'decay_rate': decay_rate,
        'n_observations': n,
        'n_segments': len(segments),
        'change_points': change_points
    }

    spectral_info = {
        'per_segment': spectral_summaries,
        'window_type': window_type
    }

    report = generate_report(seg_stats, anomaly_results, pipeline_config, spectral_info)
    write_report(report, output_path)


def main():
    """Entry point."""
    config_path = sys.argv[1] if len(sys.argv) > 1 else '/app/config.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else '/app/output.json'
    run_pipeline(config_path, output_path)


if __name__ == '__main__':
    main()
