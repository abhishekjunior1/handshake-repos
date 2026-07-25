"""
Spectral whitening for anomaly detection preprocessing.

Whitening transforms a time series so that its spectral content is
approximately flat (white), making anomalies easier to detect as
deviations from the uniform baseline.

The whitening process uses spectral residuals to identify which
frequency components are over- or under-represented relative to
the fitted envelope, then adjusts the time-domain signal accordingly.

The effective length computation accounts for energy loss due to
windowing — tapered windows reduce the effective sample size, which
affects the variance normalization of the whitened output.
"""

import math


def compute_effective_length(n, window_type):
    """Compute effective sample length after windowing.

    The effective length accounts for the energy loss introduced by
    window tapering. It equals n for rectangular (no taper) and is
    smaller for other windows, reflecting the implicit data weighting.

    Effective length = n * (mean squared window value):
        n_eff = sum(w_i^2) for normalized windows

    This equals n for rectangular, ~n/2 for Hann, ~0.54n for Hamming.

    Args:
        n: Original series length
        window_type: Name of the window function applied

    Returns:
        Integer effective length (>= 1)
    """
    if window_type == 'rectangular':
        return n

    # Compute the coherent gain (sum of squared window values / n)
    if window_type == 'hann':
        # Hann window: w_i = 0.5*(1 - cos(2*pi*i/(n-1)))
        # Sum of squares / n = 3/8 for large n
        factor = 3.0 / 8.0
    elif window_type == 'hamming':
        # Hamming: 0.54 - 0.46*cos(...)
        # Sum of squares / n ≈ 0.3974
        factor = 0.3974
    elif window_type == 'blackman':
        # Blackman: more aggressive taper
        # Sum of squares / n ≈ 0.3046
        factor = 0.3046
    else:
        factor = 1.0

    n_eff = max(1, round(n * factor))
    return n_eff


def whiten_series(series, spectral_residuals, n_effective):
    """Whiten a time series using spectral residual information.

    Applies a frequency-domain correction to flatten the spectrum.
    Points that contribute to excess spectral energy (high residuals)
    are attenuated; points at deficient frequencies are boosted.

    The whitening is approximate (time-domain proxy) — it uses the
    spectral residual magnitudes to compute per-observation weights
    based on their dominant frequency contribution.

    Args:
        series: Original time series
        spectral_residuals: Log-ratio residuals from spectral model
        n_effective: Effective sample size (for variance normalization)

    Returns:
        Whitened series (same length as input)
    """
    n = len(series)
    if n == 0:
        return []

    n_bins = len(spectral_residuals)
    if n_bins == 0:
        return list(series)

    # Compute per-observation whitening weights
    # Each observation's weight is based on how much it contributes to
    # anomalous spectral energy
    weights = _compute_whitening_weights(n, spectral_residuals)

    # Apply whitening: subtract weighted running mean, scale by sqrt(n/n_eff)
    series_mean = sum(series) / n
    scale = math.sqrt(n / n_effective) if n_effective > 0 else 1.0

    whitened = []
    for i in range(n):
        # Center and scale by local whitening weight
        centered = series[i] - series_mean
        whitened_val = centered * weights[i] / scale
        whitened.append(whitened_val)

    return whitened


def _compute_whitening_weights(n, spectral_residuals):
    """Compute per-observation whitening weights from spectral residuals.

    Maps frequency-domain residuals back to time-domain weights using
    the inverse relationship between observation position and its
    dominant frequency contribution.

    For position t, weight = exp(-|average spectral residual at t's
    dominant frequency|). High residuals → lower weight (attenuation).

    Args:
        n: Series length
        spectral_residuals: Spectral residuals (one per frequency bin)

    Returns:
        List of weights (length n)
    """
    n_bins = len(spectral_residuals)
    if n_bins == 0:
        return [1.0] * n

    # Average magnitude of spectral residuals (overall anomalousness)
    mean_abs_resid = sum(abs(r) for r in spectral_residuals) / n_bins

    weights = []
    for t in range(n):
        # Find the dominant frequency for this time position
        # Using cosine similarity to frequency basis functions
        max_contribution = 0.0
        dominant_bin = 0
        for k in range(n_bins):
            freq = (k + 1) / (2 * n_bins)
            contribution = abs(math.cos(2 * math.pi * freq * t))
            if contribution > max_contribution:
                max_contribution = contribution
                dominant_bin = k

        # Weight based on residual at dominant frequency
        resid = abs(spectral_residuals[dominant_bin])
        weight = math.exp(-resid / (mean_abs_resid + 1e-10))
        weights.append(weight)

    return weights


def compute_whiteness_test(whitened, max_lag=5):
    """Test whiteness of the transformed series via portmanteau statistic.

    Computes the Ljung-Box statistic to test whether the whitened series
    is approximately uncorrelated (white noise).

    Args:
        whitened: Whitened time series
        max_lag: Number of lags to test

    Returns:
        Dictionary with test statistic and per-lag autocorrelations
    """
    n = len(whitened)
    if n < max_lag + 3:
        return {'Q_stat': 0.0, 'acf': [0.0] * max_lag}

    mean = sum(whitened) / n
    var = sum((w - mean) ** 2 for w in whitened) / n

    if var < 1e-15:
        return {'Q_stat': 0.0, 'acf': [0.0] * max_lag}

    acf_values = []
    q_stat = 0.0
    for k in range(1, max_lag + 1):
        cov_k = sum((whitened[t] - mean) * (whitened[t - k] - mean)
                    for t in range(k, n)) / n
        rho_k = cov_k / var
        acf_values.append(rho_k)
        q_stat += (rho_k ** 2) / (n - k)

    q_stat *= n * (n + 2)

    return {'Q_stat': q_stat, 'acf': acf_values}
