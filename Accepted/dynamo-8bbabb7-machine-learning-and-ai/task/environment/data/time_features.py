"""
Time-domain statistical feature extraction for sensor signals.

Computes standard vibration analysis features: RMS (root mean square),
crest factor (peak-to-RMS ratio), and kurtosis (peakedness/tail weight).

These features characterize the amplitude distribution of the signal
and are commonly used as condition indicators for rotating machinery.
"""

import math


def compute_rms(signal):
    """Compute root mean square of a signal.

    RMS = sqrt(mean(x^2))

    Args:
        signal: List of numeric sample values

    Returns:
        RMS value (float)
    """
    n = len(signal)
    if n == 0:
        return 0.0
    return math.sqrt(sum(x ** 2 for x in signal) / n)


def compute_crest_factor(signal):
    """Compute crest factor (peak-to-RMS ratio).

    CF = max(|x|) / RMS(x)

    High crest factor indicates impulsive content (bearing faults, etc).

    Args:
        signal: List of numeric sample values

    Returns:
        Crest factor value (float >= 1.0)
    """
    if not signal:
        return 0.0

    rms = compute_rms(signal)
    if rms < 1e-15:
        return 0.0

    peak = max(abs(x) for x in signal)
    return peak / rms


def compute_kurtosis(signal):
    """Compute excess kurtosis using population moment formula.

    kurtosis = (1/n) * sum((x - mean)^4) / variance^2 - 3

    Uses population normalization (divides by n) rather than sample
    normalization (n-1). For signal processing feature extraction,
    the signal window IS the complete population of interest — we are
    characterizing THIS segment, not estimating a parameter of a larger
    process. Population moments are standard in vibration analysis and
    condition monitoring literature.

    The -3 adjustment gives Fisher's excess kurtosis (Gaussian = 0).

    Args:
        signal: List of numeric sample values

    Returns:
        Excess kurtosis value (float, 0 for Gaussian)
    """
    n = len(signal)
    if n < 4:
        return 0.0

    mean = sum(signal) / n
    variance = sum((x - mean) ** 2 for x in signal) / n

    if variance < 1e-15:
        return 0.0

    fourth_moment = sum((x - mean) ** 4 for x in signal) / n
    kurtosis = fourth_moment / (variance ** 2) - 3.0

    return kurtosis


def compute_skewness(signal):
    """Compute skewness using population moment formula.

    skewness = (1/n) * sum((x - mean)^3) / std^3

    Args:
        signal: List of numeric sample values

    Returns:
        Skewness value (float, 0 for symmetric)
    """
    n = len(signal)
    if n < 3:
        return 0.0

    mean = sum(signal) / n
    variance = sum((x - mean) ** 2 for x in signal) / n
    std = math.sqrt(variance) if variance > 0 else 0.0

    if std < 1e-15:
        return 0.0

    third_moment = sum((x - mean) ** 3 for x in signal) / n
    return third_moment / (std ** 3)


def compute_peak_to_peak(signal):
    """Compute peak-to-peak amplitude.

    Args:
        signal: List of numeric sample values

    Returns:
        Peak-to-peak value (max - min)
    """
    if not signal:
        return 0.0
    return max(signal) - min(signal)
