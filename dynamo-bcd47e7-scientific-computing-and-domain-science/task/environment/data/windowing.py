"""Window functions and segmentation for spectral analysis."""

import numpy as np


def get_window(window_type, length):
    """Generate a window function of the specified type and length."""
    if window_type == 'rectangular':
        return np.ones(length)
    elif window_type == 'hamming':
        n = np.arange(length)
        return 0.54 - 0.46 * np.cos(2.0 * np.pi * n / (length - 1))
    elif window_type == 'hann':
        n = np.arange(length)
        return 0.5 * (1.0 - np.cos(2.0 * np.pi * n / (length - 1)))
    else:
        raise ValueError(f"Unknown window type: {window_type}")


def apply_window(signal, window):
    """Apply a window function element-wise to a signal segment."""
    if len(signal) != len(window):
        raise ValueError("Signal and window must have same length")
    return signal * window


def segment_signal(signal, segment_length, overlap_ratio):
    """Split signal into overlapping segments.
    
    Parameters
    ----------
    signal : np.ndarray
        Full input signal.
    segment_length : int
        Number of samples per segment.
    overlap_ratio : float
        Fraction of overlap between consecutive segments (0 to <1).
    
    Returns
    -------
    segments : list of np.ndarray
        Signal segments (zero-padded if final segment is short).
    """
    hop_size = int(segment_length * (1.0 - overlap_ratio))
    if hop_size < 1:
        hop_size = 1
    
    segments = []
    start = 0
    while start < len(signal):
        end = start + segment_length
        if end <= len(signal):
            segments.append(signal[start:end].copy())
        else:
            # Zero-pad final segment
            seg = np.zeros(segment_length)
            seg[:len(signal) - start] = signal[start:]
            segments.append(seg)
        start += hop_size
    
    return segments


def compute_window_metrics(window):
    """Compute window normalization metrics.
    
    Returns
    -------
    metrics : dict
        coherent_gain: mean of window (amplitude correction factor)
        power_gain: mean of window squared (power correction factor)
        enbw_factor: equivalent noise bandwidth factor (N * S2/S1^2)
    """
    n = len(window)
    s1 = np.sum(window)
    s2 = np.sum(window**2)
    
    coherent_gain = s1 / n
    power_gain = s2 / n
    enbw_factor = n * s2 / (s1**2)
    
    return {
        'coherent_gain': coherent_gain,
        'power_gain': power_gain,
        'enbw_factor': enbw_factor
    }
