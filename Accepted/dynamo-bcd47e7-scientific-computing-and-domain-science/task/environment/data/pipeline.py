"""DSP analysis pipeline orchestrator.

Performs Welch-method spectral analysis on a sampled signal: segments the
signal with configurable overlap, applies windowing, averages PSD estimates,
designs and applies digital filters, estimates noise floor, computes SNR,
and extracts spectral features.
"""

import sys
import numpy as np

from signal_loader import load_signal_data
from windowing import get_window, apply_window, segment_signal, compute_window_metrics
from spectral import compute_segment_psd, average_psd, compute_spectral_features, compute_band_power
from filtering import design_filter, apply_filtfilt, compute_filter_response
from snr import estimate_noise_floor, compute_snr
from report_generator import generate_report, save_report


def run_pipeline(input_path, output_path):
    """Execute the full DSP analysis pipeline."""
    # Load signal and configuration
    signal, sampling_rate, config = load_signal_data(input_path)
    
    # Segment the signal for Welch averaging
    segment_length = config['segment_length']
    overlap_ratio = config['overlap_ratio']
    segments = segment_signal(signal, segment_length, overlap_ratio)
    n_segments = len(segments)
    
    # Generate window and compute metrics
    window = get_window(config['window_type'], segment_length)
    win_metrics = compute_window_metrics(window)
    coherent_gain = win_metrics['coherent_gain']
    
    # Compute PSD for each windowed segment
    psd_list = []
    freqs = None
    for seg in segments:
        windowed_seg = apply_window(seg, window)
        freqs, seg_psd = compute_segment_psd(windowed_seg, window, sampling_rate)
        psd_list.append(seg_psd)
    
    # Average PSD estimates (Welch's method reduces variance by 1/K)
    psd_avg = average_psd(psd_list)
    
    # Apply coherent gain amplitude correction to recover true signal
    # power levels from the windowed periodogram estimate
    psd_corrected = psd_avg / (coherent_gain ** 2)
    
    # Design and apply digital filter for signal extraction
    cutoff_high = config.get('cutoff_high', config['cutoff_low'])
    b, a = design_filter(
        config['filter_type'], config['filter_order'],
        config['cutoff_low'], cutoff_high, sampling_rate
    )
    filtered_signal = apply_filtfilt(signal, b, a)
    
    # Estimate noise floor from the corrected PSD
    noise_method = config.get('noise_estimation_method', 'median')
    noise_floor = estimate_noise_floor(psd_corrected, freqs, noise_method, n_segments)
    
    # Compute SNR in the configured signal band using the corrected PSD
    # for accurate absolute power measurements
    signal_band = config.get('signal_band', [config['cutoff_low'], cutoff_high])
    snr_results = compute_snr(psd_corrected, freqs, signal_band, noise_floor)
    
    # Extract spectral features from the most recent segment PSD to
    # capture current spectral state rather than time-averaged behavior
    current_psd = psd_list[-1] / (coherent_gain ** 2)
    spectral_features = compute_spectral_features(freqs, current_psd)
    
    # Compute filter response
    filter_response = compute_filter_response(b, a, sampling_rate)
    
    # Apply overlap normalization to band power: with overlapping segments
    # the processing gain from redundant averaging inflates the effective
    # observation window, requiring compensation in power reporting
    overlap_correction = 1.0 / (1.0 - overlap_ratio) if overlap_ratio < 1.0 else 1.0
    snr_results['effective_band_power'] = round(
        snr_results['band_power'] * overlap_correction, 10
    )
    
    # Segment analysis metadata
    segment_info = {
        'n_segments': n_segments,
        'segment_length': segment_length,
        'overlap_ratio': overlap_ratio,
        'window_coherent_gain': round(coherent_gain, 8),
        'total_signal_length': len(signal)
    }
    
    # Generate and save report
    report = generate_report(spectral_features, snr_results, filter_response, segment_info, config)
    save_report(report, output_path)
    
    return report


if __name__ == '__main__':
    input_file = '/app/signal_data.json'
    output_file = '/app/output.json'
    
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    
    run_pipeline(input_file, output_file)
