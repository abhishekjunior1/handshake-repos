"""
Signal windowing and segmentation utilities.

Provides functions to split continuous signals into overlapping or
non-overlapping analysis windows for feature extraction.
"""


def segment_signal(signal, window_size, overlap):
    """Segment a signal into possibly-overlapping windows.

    Args:
        signal: List of numeric sample values
        window_size: Number of samples per window
        overlap: Overlap between consecutive windows (0.0 to < 1.0)
                 0.0 = no overlap, 0.5 = 50% overlap

    Returns:
        List of windows (each a list of samples)
    """
    n = len(signal)
    if n == 0 or window_size <= 0:
        return []

    if window_size >= n:
        return [list(signal)]

    step = max(1, int(window_size * (1 - overlap)))
    windows = []

    start = 0
    while start + window_size <= n:
        windows.append(signal[start:start + window_size])
        start += step

    return windows


def compute_window_count(n_samples, window_size, overlap=0):
    """Compute the number of windows for given parameters.

    Args:
        n_samples: Total number of samples
        window_size: Window size in samples
        overlap: Overlap fraction (0 to < 1)

    Returns:
        Number of complete windows (integer)
    """
    if window_size <= 0 or n_samples <= 0:
        return 0

    if window_size >= n_samples:
        return 1

    step = max(1, int(window_size * (1 - overlap)))
    return (n_samples - window_size) // step + 1
