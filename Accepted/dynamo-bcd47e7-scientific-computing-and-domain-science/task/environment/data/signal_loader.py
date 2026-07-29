"""Signal data loader and validator for DSP pipeline."""

import json
import sys
import numpy as np


def load_signal_data(filepath):
    """Load signal data from a JSON file.
    
    Expected format:
    {
        "signal": [float samples],
        "sampling_rate": float (Hz),
        "config": {
            "window_type": "rectangular"|"hamming"|"hann",
            "segment_length": int,
            "overlap_ratio": float (0-1),
            "filter_type": "lowpass"|"bandpass",
            "filter_order": int,
            "cutoff_low": float (Hz),
            "cutoff_high": float (Hz),
            "noise_estimation_method": "median"|"percentile",
            "signal_band": [low_hz, high_hz]
        }
    }
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading signal data: {e}", file=sys.stderr)
        sys.exit(1)
    
    required_keys = ['signal', 'sampling_rate', 'config']
    for key in required_keys:
        if key not in data:
            print(f"Missing required key: {key}", file=sys.stderr)
            sys.exit(1)
    
    signal = np.array(data['signal'], dtype=np.float64)
    sampling_rate = float(data['sampling_rate'])
    config = data['config']
    
    _validate_signal(signal, sampling_rate)
    _validate_config(config, sampling_rate)
    
    return signal, sampling_rate, config


def _validate_signal(signal, sampling_rate):
    """Validate signal array properties."""
    if len(signal) < 16:
        print("Signal must have at least 16 samples", file=sys.stderr)
        sys.exit(1)
    if sampling_rate <= 0:
        print("Sampling rate must be positive", file=sys.stderr)
        sys.exit(1)
    if not np.all(np.isfinite(signal)):
        print("Signal contains non-finite values", file=sys.stderr)
        sys.exit(1)


def _validate_config(config, sampling_rate):
    """Validate configuration parameters."""
    nyquist = sampling_rate / 2.0
    
    valid_windows = ['rectangular', 'hamming', 'hann']
    if config.get('window_type') not in valid_windows:
        print(f"Invalid window type: {config.get('window_type')}", file=sys.stderr)
        sys.exit(1)
    
    seg_len = config.get('segment_length', 0)
    if not isinstance(seg_len, int) or seg_len < 16:
        print("segment_length must be >= 16", file=sys.stderr)
        sys.exit(1)
    
    overlap = config.get('overlap_ratio', 0.0)
    if not (0.0 <= overlap < 1.0):
        print("overlap_ratio must be in [0, 1)", file=sys.stderr)
        sys.exit(1)
    
    valid_filters = ['lowpass', 'bandpass']
    if config.get('filter_type') not in valid_filters:
        print(f"Invalid filter type: {config.get('filter_type')}", file=sys.stderr)
        sys.exit(1)
    
    order = config.get('filter_order', 0)
    if not isinstance(order, int) or order < 1:
        print("filter_order must be positive", file=sys.stderr)
        sys.exit(1)
    
    cutoff_low = config.get('cutoff_low', 0)
    if cutoff_low <= 0 or cutoff_low >= nyquist:
        print(f"cutoff_low must be in (0, {nyquist})", file=sys.stderr)
        sys.exit(1)
    
    if config['filter_type'] == 'bandpass':
        cutoff_high = config.get('cutoff_high', 0)
        if cutoff_high <= cutoff_low or cutoff_high >= nyquist:
            print(f"cutoff_high must be in ({cutoff_low}, {nyquist})", file=sys.stderr)
            sys.exit(1)
    
    if 'signal_band' in config:
        band = config['signal_band']
        if len(band) != 2 or band[0] >= band[1]:
            print("signal_band must be [low, high]", file=sys.stderr)
            sys.exit(1)
