"""
Cross-channel correlation feature extraction.

Computes pairwise correlation and coherence between sensor channels
to capture mechanical coupling, vibration transfer paths, and
synchronization patterns across measurement points.

The correlation features are computed on DETRENDED signals to isolate
the dynamic (oscillatory) correlation from static trend relationships.
The caller is responsible for passing appropriately preprocessed signals.
"""

import math


def detrend_signal(signal):
    """Remove linear trend from signal.

    Fits a linear model y = a*t + b and subtracts it.
    This isolates the oscillatory/dynamic content from slow drifts.

    Args:
        signal: List of numeric values

    Returns:
        Detrended signal (same length)
    """
    n = len(signal)
    if n < 2:
        return list(signal)

    # Fit linear trend: y = a*t + b
    # Using normal equations for t = 0, 1, ..., n-1
    t_mean = (n - 1) / 2.0
    y_mean = sum(signal) / n

    numerator = sum((t - t_mean) * (signal[t] - y_mean) for t in range(n))
    denominator = sum((t - t_mean) ** 2 for t in range(n))

    if abs(denominator) < 1e-15:
        slope = 0.0
    else:
        slope = numerator / denominator

    intercept = y_mean - slope * t_mean

    # Subtract trend
    detrended = [signal[t] - (slope * t + intercept) for t in range(n)]
    return detrended


def compute_cross_correlation(signal_a, signal_b):
    """Compute Pearson correlation between two signals.

    This function computes correlation on whatever signals are passed.
    For dynamic correlation (excluding trend effects), the caller should
    pass detrended signals. For total correlation (including trends),
    pass raw signals.

    Args:
        signal_a: First signal (list of floats)
        signal_b: Second signal (same length)

    Returns:
        Pearson correlation coefficient (-1 to 1)
    """
    n = min(len(signal_a), len(signal_b))
    if n < 3:
        return 0.0

    mean_a = sum(signal_a[:n]) / n
    mean_b = sum(signal_b[:n]) / n

    cov = sum((signal_a[i] - mean_a) * (signal_b[i] - mean_b) for i in range(n))
    var_a = sum((signal_a[i] - mean_a) ** 2 for i in range(n))
    var_b = sum((signal_b[i] - mean_b) ** 2 for i in range(n))

    denom = math.sqrt(var_a * var_b)
    if denom < 1e-15:
        return 0.0

    return cov / denom


def compute_coherence(signal_a, signal_b, sample_rate):
    """Compute magnitude-squared coherence at the dominant frequency.

    Coherence measures linear frequency-domain coupling between channels.
    Returns the coherence value at the frequency with maximum cross-spectral
    density.

    Args:
        signal_a: First channel signal
        signal_b: Second channel signal
        sample_rate: Sampling frequency

    Returns:
        Coherence value at dominant frequency (0 to 1)
    """
    n = min(len(signal_a), len(signal_b))
    if n < 4:
        return 0.0

    mean_a = sum(signal_a[:n]) / n
    mean_b = sum(signal_b[:n]) / n
    ca = [signal_a[i] - mean_a for i in range(n)]
    cb = [signal_b[i] - mean_b for i in range(n)]

    # Find dominant frequency via cross-spectrum
    max_cross_power = 0.0
    max_k = 1
    n_bins = n // 2

    for k in range(1, n_bins + 1):
        # DFT of signal A at frequency k
        ra = sum(ca[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        ia = -sum(ca[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))

        # DFT of signal B at frequency k
        rb = sum(cb[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
        ib = -sum(cb[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))

        # Cross-spectral density magnitude
        cross_real = ra * rb + ia * ib
        cross_imag = ia * rb - ra * ib
        cross_power = math.sqrt(cross_real ** 2 + cross_imag ** 2)

        if cross_power > max_cross_power:
            max_cross_power = cross_power
            max_k = k

    # Compute coherence at dominant frequency
    k = max_k
    ra = sum(ca[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
    ia = -sum(ca[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))
    rb = sum(cb[t] * math.cos(2 * math.pi * k * t / n) for t in range(n))
    ib = -sum(cb[t] * math.sin(2 * math.pi * k * t / n) for t in range(n))

    power_a = ra ** 2 + ia ** 2
    power_b = rb ** 2 + ib ** 2

    cross_real = ra * rb + ia * ib
    cross_imag = ia * rb - ra * ib
    cross_power_sq = cross_real ** 2 + cross_imag ** 2

    denom = power_a * power_b
    if denom < 1e-15:
        return 0.0

    coherence = cross_power_sq / denom
    return min(1.0, coherence)
