"""Spectral Whitening module for the anomaly detection pipeline.

Implements Nadaraya-Watson kernel regression for spectral whitening,
which normalizes the observed spectral density by the smooth AR
envelope to produce whitened residuals. Includes temporal relevance
decay weighting to emphasize recent spectral behavior.

Whitened spectral residual at frequency f:
    W(f) = S_obs(f) / S_AR(f) * decay_weight(t)

The temporal decay ensures that anomalies in recent observations
contribute more to the detection score than historical patterns,
reflecting the non-stationarity of real-world time series.
"""

import math
from typing import List, Dict, Optional, Tuple


class WhiteningError(Exception):
    """Raised when spectral whitening encounters an error."""
    pass


def gaussian_kernel(x: float, bandwidth: float) -> float:
    """Evaluate the Gaussian kernel at point x.

    K(x) = (1/sqrt(2*pi)) * exp(-x^2 / (2*h^2))

    Args:
        x: Evaluation point.
        bandwidth: Kernel bandwidth parameter h.

    Returns:
        Kernel value.
    """
    if bandwidth <= 0:
        raise WhiteningError("Bandwidth must be positive")
    z = x / bandwidth
    return math.exp(-0.5 * z * z) / (math.sqrt(2.0 * math.pi) * bandwidth)


def nadaraya_watson_smooth(frequencies: List[float],
                           values: List[float],
                           bandwidth: float) -> List[float]:
    """Apply Nadaraya-Watson kernel regression smoothing.

    Computes the kernel-weighted local average:
        m(x) = sum_i K((x - x_i)/h) * y_i / sum_i K((x - x_i)/h)

    This provides a nonparametric smooth of the spectral density
    that adapts to local structure in the frequency domain.

    Args:
        frequencies: Frequency grid points.
        values: Spectral values at each frequency.
        bandwidth: Kernel bandwidth for smoothing.

    Returns:
        Smoothed spectral values.
    """
    n = len(frequencies)
    if n != len(values):
        raise WhiteningError("Frequencies and values must have same length")
    if n == 0:
        return []

    smoothed = []
    for i in range(n):
        numerator = 0.0
        denominator = 0.0
        for j in range(n):
            k_val = gaussian_kernel(frequencies[i] - frequencies[j], bandwidth)
            numerator += k_val * values[j]
            denominator += k_val

        if denominator > 1e-15:
            smoothed.append(numerator / denominator)
        else:
            smoothed.append(values[i])

    return smoothed


def compute_temporal_decay_weights(n_observations: int,
                                   decay_rate: float = 0.05
                                   ) -> List[float]:
    """Compute exponential temporal relevance decay weights.

    Applies exponential decay so that more recent observations
    receive higher weight in the anomaly scoring. This reflects
    the principle that recent behavior is more indicative of
    current system state than historical patterns.

    Weight for observation at position t (0-indexed from oldest):
        w(t) = exp(-decay_rate * (n - 1 - t))

    Weights are normalized to sum to n_observations to preserve
    the overall scale of the anomaly scores.

    Args:
        n_observations: Number of observations.
        decay_rate: Exponential decay rate parameter.

    Returns:
        List of decay weights (oldest to newest).
    """
    if n_observations <= 0:
        return []

    weights = []
    for t in range(n_observations):
        # Distance from most recent observation
        distance = n_observations - 1 - t
        w = math.exp(-decay_rate * distance)
        weights.append(w)

    # Normalize to preserve score scale
    total = sum(weights)
    if total > 0:
        scale = n_observations / total
        weights = [w * scale for w in weights]

    return weights


def compute_whitened_residuals(observed_power: List[float],
                              ar_spectrum: List[float],
                              frequencies: List[float],
                              bandwidth: float = 0.3
                              ) -> Dict[str, object]:
    """Compute whitened spectral residuals.

    The whitening process:
    1. Smooth the AR spectrum via Nadaraya-Watson regression
    2. Divide observed power by smoothed AR envelope
    3. The residuals should be approximately chi-squared(2)/2
       under the null hypothesis of no anomaly

    Args:
        observed_power: Observed periodogram values.
        ar_spectrum: AR model spectral density values.
        frequencies: Frequency grid.
        bandwidth: Kernel bandwidth for smoothing.

    Returns:
        Dictionary with:
            'residuals': whitened spectral residuals
            'smooth_envelope': smoothed AR spectrum
            'raw_ratio': unsmoothed power/envelope ratio
    """
    n = len(observed_power)
    if n != len(ar_spectrum) or n != len(frequencies):
        raise WhiteningError("Input arrays must have equal length")

    # Smooth the AR envelope for robust division
    smooth_envelope = nadaraya_watson_smooth(frequencies, ar_spectrum, bandwidth)

    # Compute whitened residuals
    residuals = []
    raw_ratios = []
    for i in range(n):
        env = smooth_envelope[i]
        if env < 1e-15:
            env = 1e-15  # Prevent division by zero

        ratio = observed_power[i] / env
        raw_ratios.append(ratio)
        residuals.append(ratio)

    return {
        'residuals': residuals,
        'smooth_envelope': smooth_envelope,
        'raw_ratio': raw_ratios
    }


def apply_decay_weighting(scores: List[float],
                          decay_rate: float = 0.05) -> List[float]:
    """Apply temporal relevance decay to anomaly scores.

    Weights scores by exponential decay based on temporal position,
    giving more weight to recent observations. This is standard
    practice in online anomaly detection where recent deviations
    are more actionable than historical ones.

    Args:
        scores: Raw anomaly scores (ordered oldest to newest).
        decay_rate: Exponential decay rate.

    Returns:
        Decay-weighted anomaly scores.
    """
    n = len(scores)
    if n == 0:
        return []

    weights = compute_temporal_decay_weights(n, decay_rate)
    weighted = [s * w for s, w in zip(scores, weights)]

    return weighted


def compute_spectral_flatness(power: List[float]) -> float:
    """Compute spectral flatness measure (Wiener entropy).

    Spectral flatness = geometric_mean(S) / arithmetic_mean(S)

    Values near 1.0 indicate white noise (flat spectrum);
    values near 0.0 indicate tonal/narrowband content.

    Args:
        power: Spectral power values.

    Returns:
        Spectral flatness in [0, 1].
    """
    n = len(power)
    if n == 0:
        return 0.0

    # Filter out non-positive values
    positive = [p for p in power if p > 1e-15]
    if not positive:
        return 0.0

    # Geometric mean via log
    log_sum = sum(math.log(p) for p in positive)
    geo_mean = math.exp(log_sum / len(positive))

    # Arithmetic mean
    arith_mean = sum(positive) / len(positive)

    if arith_mean < 1e-15:
        return 0.0

    return geo_mean / arith_mean
