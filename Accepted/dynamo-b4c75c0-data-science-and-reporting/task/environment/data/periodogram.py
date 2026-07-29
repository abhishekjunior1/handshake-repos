"""
Periodogram computation and window functions for spectral analysis.

Implements the standard periodogram estimator for power spectral density
and several common window (taper) functions for spectral leakage control.

The periodogram is computed as |DFT(x)|^2 / n for each positive frequency.
Window functions are applied before the DFT to reduce spectral leakage
from non-periodic boundary effects.

Supported windows: rectangular (no taper), hann, hamming, blackman.
"""

import math


def apply_window(series, window_type):
    """Apply a window function to the time series before spectral analysis.

    Window functions taper the series toward zero at the endpoints, reducing
    spectral leakage in the periodogram at the cost of frequency resolution.

    The rectangular window is the identity (no modification) — use this when
    the series is already periodic or when maximum frequency resolution is
    needed and leakage is acceptable.

    Args:
        series: Input time series values
        window_type: One of 'rectangular', 'hann', 'hamming', 'blackman'

    Returns:
        Windowed series (same length)
    """
    n = len(series)
    if n == 0:
        return []

    if window_type == 'rectangular':
        return list(series)

    # Compute window coefficients
    window = _compute_window(n, window_type)

    # Apply window (element-wise multiplication)
    return [series[i] * window[i] for i in range(n)]


def _compute_window(n, window_type):
    """Compute window function coefficients.

    Args:
        n: Window length
        window_type: Window name

    Returns:
        List of window coefficients
    """
    if window_type == 'hann':
        return [0.5 * (1 - math.cos(2 * math.pi * i / (n - 1)))
                for i in range(n)]
    elif window_type == 'hamming':
        return [0.54 - 0.46 * math.cos(2 * math.pi * i / (n - 1))
                for i in range(n)]
    elif window_type == 'blackman':
        return [0.42 - 0.5 * math.cos(2 * math.pi * i / (n - 1))
                + 0.08 * math.cos(4 * math.pi * i / (n - 1))
                for i in range(n)]
    else:
        # Default to rectangular
        return [1.0] * n


def compute_periodogram(windowed_series):
    """Compute the periodogram (power spectral density estimate).

    Computes |X(k)|^2 / n for each frequency index k from 1 to n//2,
    where X(k) is the DFT of the input series.

    The output represents power at each frequency bin. The caller
    may apply additional normalizations (e.g., division by 2*pi for
    angular frequency density).

    Args:
        windowed_series: Time series after window application

    Returns:
        List of periodogram values (length n//2), one per frequency bin
    """
    n = len(windowed_series)
    if n < 2:
        return [0.0]

    # Mean-center to remove DC component
    mean = sum(windowed_series) / n
    centered = [x - mean for x in windowed_series]

    periodogram = []
    for k in range(1, n // 2 + 1):
        real_part = 0.0
        imag_part = 0.0
        for t in range(n):
            angle = 2 * math.pi * k * t / n
            real_part += centered[t] * math.cos(angle)
            imag_part -= centered[t] * math.sin(angle)

        # Periodogram: |X(k)|^2 / n
        power = (real_part ** 2 + imag_part ** 2) / n
        periodogram.append(power)

    return periodogram


def compute_frequency_axis(n):
    """Compute the frequency values corresponding to periodogram bins.

    Returns frequencies in cycles per sample (0 to 0.5).

    Args:
        n: Original series length

    Returns:
        List of frequency values
    """
    return [k / n for k in range(1, n // 2 + 1)]


def compute_period_axis(n):
    """Compute the period values corresponding to periodogram bins.

    Returns periods in samples per cycle.

    Args:
        n: Original series length

    Returns:
        List of period values
    """
    return [n / k for k in range(1, n // 2 + 1)]
