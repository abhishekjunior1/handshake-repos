"""Spectral Estimator module for the anomaly detection pipeline.

Computes periodogram-based spectral density estimates from time series
segments using the Discrete Fourier Transform (DFT). Supports multiple
windowing functions for sidelobe control.

The spectral density is estimated as:
    S(f) = (1 / (2*pi*n_eff)) * |X(f)|^2

where X(f) is the DFT of the windowed series, n_eff is the effective
sample size accounting for window energy loss, and the 2*pi factor
converts from angular frequency to ordinary frequency density.
"""

import math
from typing import List, Tuple, Dict, Optional


class SpectralEstimationError(Exception):
    """Raised when spectral estimation encounters invalid input."""
    pass


def compute_window(window_type: str, n: int) -> List[float]:
    """Generate a window function of length n.

    Supported types:
        'rectangular' - uniform weights (no tapering)
        'hann' - Hann (raised cosine) window
        'hamming' - Hamming window

    Args:
        window_type: Name of the window function.
        n: Length of the window.

    Returns:
        List of window coefficients.
    """
    if n <= 0:
        raise SpectralEstimationError("Window length must be positive")

    if window_type == 'rectangular':
        return [1.0] * n
    elif window_type == 'hann':
        return [0.5 * (1.0 - math.cos(2.0 * math.pi * k / (n - 1)))
                for k in range(n)]
    elif window_type == 'hamming':
        return [0.54 - 0.46 * math.cos(2.0 * math.pi * k / (n - 1))
                for k in range(n)]
    else:
        raise SpectralEstimationError(f"Unknown window type: {window_type}")


def compute_effective_sample_size(window: List[float]) -> float:
    """Compute the effective sample size for a given window.

    The effective sample size accounts for the energy loss due to
    windowing. For a rectangular window, n_eff = n. For tapered
    windows, n_eff < n.

    Formula: n_eff = (sum(w_i))^2 / sum(w_i^2)

    Args:
        window: List of window coefficients.

    Returns:
        Effective sample size as a float.
    """
    if not window:
        raise SpectralEstimationError("Empty window")

    sum_w = sum(window)
    sum_w2 = sum(w * w for w in window)

    if sum_w2 == 0:
        raise SpectralEstimationError("Window has zero energy")

    return (sum_w * sum_w) / sum_w2


def apply_window(series: List[float], window: List[float]) -> List[float]:
    """Apply a window function to a time series segment.

    Args:
        series: Input time series values.
        window: Window coefficients (same length as series).

    Returns:
        Windowed series.
    """
    if len(series) != len(window):
        raise SpectralEstimationError(
            f"Series length ({len(series)}) != window length ({len(window)})"
        )
    return [s * w for s, w in zip(series, window)]


def compute_dft(signal: List[float]) -> List[complex]:
    """Compute the Discrete Fourier Transform of a real-valued signal.

    Uses direct DFT computation (not FFT) for clarity and correctness
    on arbitrary-length inputs.

    Args:
        signal: Real-valued input signal.

    Returns:
        List of complex DFT coefficients.
    """
    n = len(signal)
    if n == 0:
        return []

    dft_coeffs = []
    for k in range(n):
        real_part = 0.0
        imag_part = 0.0
        for t in range(n):
            angle = -2.0 * math.pi * k * t / n
            real_part += signal[t] * math.cos(angle)
            imag_part += signal[t] * math.sin(angle)
        dft_coeffs.append(complex(real_part, imag_part))

    return dft_coeffs


def compute_periodogram(series: List[float], window_type: str = 'rectangular'
                        ) -> Dict[str, object]:
    """Compute the periodogram spectral density estimate.

    The spectral density is normalized by dividing by (2*pi * n_eff),
    which converts the raw periodogram power to angular frequency
    density units consistent with the AR spectral envelope fitting.

    Args:
        series: Input time series segment.
        window_type: Window function to apply before DFT.

    Returns:
        Dictionary with keys:
            'frequencies': list of frequency bins (0 to pi)
            'power': list of spectral density values
            'n_effective': effective sample size after windowing
            'window_type': the window used
    """
    n = len(series)
    if n < 4:
        raise SpectralEstimationError("Series too short for spectral estimation")

    # Generate and apply window
    window = compute_window(window_type, n)
    windowed = apply_window(series, window)

    # Compute effective sample size
    n_eff = compute_effective_sample_size(window)

    # Compute DFT
    dft_coeffs = compute_dft(windowed)

    # Compute one-sided periodogram (frequencies 0 to pi)
    n_freqs = n // 2 + 1
    frequencies = [math.pi * k / (n // 2) for k in range(n_freqs)]

    # Spectral density: |X(f)|^2 / (2*pi*n_eff)
    # The 2*pi normalization converts to angular frequency density
    # consistent with the AR model's spectral envelope representation
    power = []
    for k in range(n_freqs):
        mag_squared = (dft_coeffs[k].real ** 2 + dft_coeffs[k].imag ** 2)
        # Normalize by 2*pi*n_eff for proper angular frequency density
        psd = mag_squared / (2.0 * math.pi * n_eff)
        power.append(psd)

    return {
        'frequencies': frequencies,
        'power': power,
        'n_effective': n_eff,
        'window_type': window_type
    }


def compute_cross_spectral_density(series_a: List[float],
                                    series_b: List[float],
                                    window_type: str = 'rectangular'
                                    ) -> Dict[str, object]:
    """Compute the cross-spectral density between two series.

    Used for coherence estimation in multi-channel anomaly detection.

    Args:
        series_a: First input series.
        series_b: Second input series.
        window_type: Window function.

    Returns:
        Dictionary with cross-spectral density information.
    """
    if len(series_a) != len(series_b):
        raise SpectralEstimationError("Series must have equal length")

    n = len(series_a)
    window = compute_window(window_type, n)
    n_eff = compute_effective_sample_size(window)

    windowed_a = apply_window(series_a, window)
    windowed_b = apply_window(series_b, window)

    dft_a = compute_dft(windowed_a)
    dft_b = compute_dft(windowed_b)

    n_freqs = n // 2 + 1
    frequencies = [math.pi * k / (n // 2) for k in range(n_freqs)]

    cross_power = []
    for k in range(n_freqs):
        # Cross-spectral density: X_a(f) * conj(X_b(f)) / (2*pi*n_eff)
        cross = dft_a[k] * dft_b[k].conjugate()
        csd = abs(cross) / (2.0 * math.pi * n_eff)
        cross_power.append(csd)

    return {
        'frequencies': frequencies,
        'cross_power': cross_power,
        'n_effective': n_eff
    }
