"""
Frequency-domain feature extraction for sensor signals.

Computes spectral features from the signal's power spectrum: spectral
centroid (center of mass), bandwidth (spectral spread), rolloff frequency,
and band energy (power in specific frequency ranges).

Uses DFT-based periodogram for spectral estimation.
"""

import math


def _compute_power_spectrum(signal, sample_rate):
    """Compute one-sided power spectrum via DFT.

    Returns frequencies and corresponding power values.

    Args:
        signal: Time-domain signal values
        sample_rate: Sampling frequency in Hz

    Returns:
        Tuple of (frequencies, powers) lists
    """
    n = len(signal)
    if n < 2:
        return [0.0], [0.0]

    # Mean-center
    mean = sum(signal) / n
    centered = [x - mean for x in signal]

    # DFT (positive frequencies only)
    n_bins = n // 2
    frequencies = []
    powers = []

    for k in range(1, n_bins + 1):
        freq = k * sample_rate / n
        real_part = 0.0
        imag_part = 0.0
        for t in range(n):
            angle = 2 * math.pi * k * t / n
            real_part += centered[t] * math.cos(angle)
            imag_part -= centered[t] * math.sin(angle)

        power = (real_part ** 2 + imag_part ** 2) / n
        frequencies.append(freq)
        powers.append(power)

    return frequencies, powers


def compute_spectral_centroid(signal, sample_rate):
    """Compute spectral centroid (center of mass of the spectrum).

    SC = sum(f * P(f)) / sum(P(f))

    Represents the "average frequency" weighted by power.

    Args:
        signal: Time-domain signal values
        sample_rate: Sampling frequency in Hz

    Returns:
        Spectral centroid in Hz
    """
    frequencies, powers = _compute_power_spectrum(signal, sample_rate)
    total_power = sum(powers)

    if total_power < 1e-15:
        return 0.0

    centroid = sum(f * p for f, p in zip(frequencies, powers)) / total_power
    return centroid


def compute_spectral_bandwidth(signal, sample_rate, centroid):
    """Compute spectral bandwidth (spectral spread around centroid).

    BW = sqrt(sum((f - centroid)^2 * P(f)) / sum(P(f)))

    Args:
        signal: Time-domain signal values
        sample_rate: Sampling frequency in Hz
        centroid: Pre-computed spectral centroid

    Returns:
        Spectral bandwidth in Hz
    """
    frequencies, powers = _compute_power_spectrum(signal, sample_rate)
    total_power = sum(powers)

    if total_power < 1e-15:
        return 0.0

    variance = sum((f - centroid) ** 2 * p for f, p in zip(frequencies, powers)) / total_power
    return math.sqrt(variance)


def compute_spectral_rolloff(signal, sample_rate, threshold=0.85):
    """Compute spectral rolloff frequency.

    The frequency below which 'threshold' fraction of total spectral
    energy is contained. The threshold is configurable — use 0.85 for
    vibration analysis (primary modes), 0.95 for audio/speech.

    Args:
        signal: Time-domain signal values
        sample_rate: Sampling frequency in Hz
        threshold: Energy fraction (0 to 1), default 0.85

    Returns:
        Rolloff frequency in Hz
    """
    frequencies, powers = _compute_power_spectrum(signal, sample_rate)
    total_power = sum(powers)

    if total_power < 1e-15:
        return 0.0

    target = threshold * total_power
    cumulative = 0.0

    for freq, power in zip(frequencies, powers):
        cumulative += power
        if cumulative >= target:
            return freq

    return frequencies[-1] if frequencies else 0.0


def compute_band_energy(signal, sample_rate, low_freq, high_freq):
    """Compute spectral energy in a specific frequency band.

    Sum of power spectral density values within [low_freq, high_freq].

    Args:
        signal: Time-domain signal values
        sample_rate: Sampling frequency in Hz
        low_freq: Lower band boundary in Hz
        high_freq: Upper band boundary in Hz

    Returns:
        Band energy value
    """
    frequencies, powers = _compute_power_spectrum(signal, sample_rate)

    band_energy = sum(p for f, p in zip(frequencies, powers)
                      if low_freq <= f <= high_freq)

    return band_energy
