"""
Iterative frequency estimation for harmonic decomposition.

Detects dominant harmonic frequencies in a time series using
iterative periodogram peak-picking with spectral leakage correction.
Each iteration removes the strongest detected frequency and re-estimates
the residual spectrum to find secondary harmonics.

The effective sample size accounts for windowing effects:
    n_effective = (sum(w))^2 / sum(w^2)
where w is the observation weight/window vector. For rectangular
windows n_effective = n; for tapered windows n_effective < n.
"""

import math


def estimate_frequencies(series, max_harmonics, window_type='rectangular'):
    """Estimate dominant frequencies via iterative periodogram analysis.

    Applies a spectral window, computes the periodogram, picks the
    strongest peak, subtracts that harmonic, and repeats.

    Args:
        series: Input time series (list of floats).
        max_harmonics: Maximum number of harmonics to extract.
        window_type: Spectral window ('rectangular', 'hann', 'hamming').

    Returns:
        Dictionary with:
            - frequencies: list of detected frequencies (cycles/sample)
            - powers: spectral power at each frequency
            - n_effective: effective sample size after windowing
            - window_weights: applied window function values
    """
    n = len(series)
    window = compute_window(n, window_type)
    n_effective = compute_effective_length(n, window)

    # Iterative frequency extraction
    residual = list(series)
    frequencies = []
    powers = []

    for _ in range(max_harmonics):
        # Apply window and compute periodogram
        windowed = [residual[t] * window[t] for t in range(n)]
        freq, power = find_peak_frequency(windowed, n)

        if power < 1e-10:
            break

        frequencies.append(freq)
        powers.append(power)

        # Subtract this harmonic from residual
        residual = subtract_harmonic(residual, freq, n)

    return {
        'frequencies': frequencies,
        'powers': powers,
        'n_effective': n_effective,
        'window_weights': window
    }


def compute_window(n, window_type):
    """Compute spectral window function.

    Args:
        n: Window length.
        window_type: Type of window.

    Returns:
        List of window weights.
    """
    if window_type == 'rectangular':
        return [1.0] * n
    elif window_type == 'hann':
        return [0.5 * (1.0 - math.cos(2 * math.pi * t / (n - 1)))
                for t in range(n)]
    elif window_type == 'hamming':
        return [0.54 - 0.46 * math.cos(2 * math.pi * t / (n - 1))
                for t in range(n)]
    else:
        return [1.0] * n


def compute_effective_length(n, window):
    """Compute effective sample size for a given window.

    The effective length accounts for the variance inflation caused
    by tapering. For a rectangular window, n_effective = n.

        n_effective = (sum(w_t))^2 / sum(w_t^2)

    Args:
        n: Nominal sample size.
        window: Window weight vector.

    Returns:
        Effective sample size (float).
    """
    sum_w = sum(window)
    sum_w2 = sum(w * w for w in window)

    if sum_w2 == 0:
        return float(n)

    return (sum_w * sum_w) / sum_w2


def find_peak_frequency(windowed_series, n):
    """Find the frequency with maximum spectral power.

    Computes the DFT-based periodogram and returns the frequency
    and power of the strongest peak (excluding DC).

    Args:
        windowed_series: Windowed time series.
        n: Original series length.

    Returns:
        Tuple of (frequency_in_cycles_per_sample, power).
    """
    # Compute periodogram via DFT
    n_freq = n // 2
    max_power = 0.0
    max_freq = 0.0

    for k in range(1, n_freq + 1):
        # DFT at frequency k/n
        real_part = sum(windowed_series[t] * math.cos(2 * math.pi * k * t / n)
                        for t in range(n))
        imag_part = sum(windowed_series[t] * math.sin(2 * math.pi * k * t / n)
                        for t in range(n))

        power = (real_part ** 2 + imag_part ** 2) / n

        if power > max_power:
            max_power = power
            max_freq = k / n

    return max_freq, max_power


def subtract_harmonic(series, frequency, n):
    """Subtract a harmonic component at the given frequency.

    Estimates amplitude and phase via least-squares projection,
    then subtracts the fitted sinusoid.

    Args:
        series: Current residual series.
        frequency: Frequency to remove (cycles/sample).
        n: Series length.

    Returns:
        Residual series after harmonic subtraction.
    """
    # Least-squares fit: a*cos(2*pi*f*t) + b*sin(2*pi*f*t)
    cos_sum = 0.0
    sin_sum = 0.0
    cos2_sum = 0.0
    sin2_sum = 0.0
    cos_sin_sum = 0.0

    for t in range(n):
        c = math.cos(2 * math.pi * frequency * t)
        s = math.sin(2 * math.pi * frequency * t)
        cos_sum += series[t] * c
        sin_sum += series[t] * s
        cos2_sum += c * c
        sin2_sum += s * s
        cos_sin_sum += c * s

    # Solve 2x2 system
    det = cos2_sum * sin2_sum - cos_sin_sum ** 2
    if abs(det) < 1e-15:
        return series

    a = (sin2_sum * cos_sum - cos_sin_sum * sin_sum) / det
    b = (cos2_sum * sin_sum - cos_sin_sum * cos_sum) / det

    # Subtract
    result = [series[t] - a * math.cos(2 * math.pi * frequency * t)
              - b * math.sin(2 * math.pi * frequency * t)
              for t in range(n)]

    return result


def compute_frequency_resolution(n, window_type):
    """Compute the frequency resolution for the given configuration.

    The resolution determines the minimum detectable frequency
    separation between distinct harmonics.

    Args:
        n: Series length.
        window_type: Applied window type.

    Returns:
        Frequency resolution in cycles/sample.
    """
    # Base resolution is 1/n
    base_resolution = 1.0 / n

    # Tapered windows widen the main lobe
    lobe_widths = {
        'rectangular': 1.0,
        'hann': 2.0,
        'hamming': 1.81
    }
    multiplier = lobe_widths.get(window_type, 1.0)

    return base_resolution * multiplier
