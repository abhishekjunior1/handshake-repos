"""
Non-parametric trend extraction for harmonic decomposition.

Implements locally-weighted regression (LOESS-style) for extracting
the slowly-varying trend component from a time series. The trend
is estimated adaptively: the bandwidth parameter controls the degree
of smoothing and should reflect the local stationarity regime.

For stationary series, a single global bandwidth suffices. For
non-stationary series with regime changes, per-segment adaptive
bandwidths provide better trend estimates.
"""

import math


def extract_trend(series, bandwidth, window_weights=None):
    """Extract trend component via local polynomial regression.

    Uses a Nadaraya-Watson kernel smoother with Gaussian kernel.
    The bandwidth controls the effective window width — larger
    bandwidth = smoother trend, smaller = more responsive.

    Args:
        series: Input time series.
        bandwidth: Smoothing bandwidth (fraction of series length).
        window_weights: Optional observation weights.

    Returns:
        Dictionary with:
            - trend: estimated trend values
            - detrended: series minus trend
            - effective_bandwidth: actual bandwidth used
    """
    n = len(series)
    if window_weights is None:
        window_weights = [1.0] * n

    h = max(1.0, bandwidth * n)  # Bandwidth in observation units
    trend = []

    for t in range(n):
        # Kernel-weighted local mean
        numerator = 0.0
        denominator = 0.0

        for s in range(n):
            distance = abs(t - s) / h
            kernel_weight = gaussian_kernel(distance)
            total_weight = kernel_weight * window_weights[s]

            numerator += total_weight * series[s]
            denominator += total_weight

        if denominator > 0:
            trend.append(numerator / denominator)
        else:
            trend.append(series[t])

    detrended = [series[t] - trend[t] for t in range(n)]

    return {
        'trend': [round(t, 6) for t in trend],
        'detrended': [round(d, 6) for d in detrended],
        'effective_bandwidth': round(h, 6)
    }


def gaussian_kernel(u):
    """Gaussian kernel function for smoothing.

    K(u) = exp(-u^2 / 2) / sqrt(2*pi)

    Args:
        u: Normalized distance.

    Returns:
        Kernel weight.
    """
    if abs(u) > 4.0:  # Truncate for efficiency
        return 0.0
    return math.exp(-u * u / 2.0) / math.sqrt(2 * math.pi)


def compute_adaptive_bandwidth(series, segment_boundaries):
    """Compute per-segment adaptive bandwidths.

    For each segment between boundaries, estimates an optimal
    bandwidth based on local variability. Higher variability
    segments get smaller bandwidth (less smoothing) to preserve
    local structure.

    Args:
        series: Input time series.
        segment_boundaries: List of segment start indices.

    Returns:
        List of (start, end, bandwidth) tuples for each segment.
    """
    n = len(series)
    if not segment_boundaries:
        return [(0, n, 0.15)]  # Default global bandwidth

    # Build segments
    boundaries = sorted(segment_boundaries) + [n]
    segments = []
    prev = 0

    for boundary in boundaries:
        if boundary > prev:
            seg_data = series[prev:boundary]
            seg_len = len(seg_data)

            if seg_len < 3:
                bw = 0.5
            else:
                # Bandwidth inversely proportional to local variability
                seg_mean = sum(seg_data) / seg_len
                seg_var = sum((x - seg_mean) ** 2 for x in seg_data) / seg_len
                seg_cv = math.sqrt(seg_var) / abs(seg_mean) if abs(seg_mean) > 1e-10 else 1.0

                # Higher CV → smaller bandwidth (less smoothing)
                bw = max(0.05, min(0.4, 0.2 / (1.0 + seg_cv)))

            segments.append((prev, boundary, round(bw, 6)))
            prev = boundary

    return segments


def compute_trend_diagnostics(series, trend, detrended):
    """Compute diagnostics for the trend extraction.

    Args:
        series: Original series.
        trend: Extracted trend.
        detrended: Residual after trend removal.

    Returns:
        Dictionary of trend diagnostics.
    """
    n = len(series)

    # Trend smoothness: ratio of trend variance to series variance
    series_var = sum((x - sum(series) / n) ** 2 for x in series) / n
    trend_mean = sum(trend) / n
    trend_var = sum((t - trend_mean) ** 2 for t in trend) / n

    if series_var > 0:
        trend_ratio = trend_var / series_var
    else:
        trend_ratio = 0.0

    # Detrended stationarity indicator
    detrend_mean = sum(detrended) / n
    detrend_var = sum((d - detrend_mean) ** 2 for d in detrended) / n

    return {
        'trend_variance_ratio': round(trend_ratio, 6),
        'detrended_variance': round(detrend_var, 6),
        'trend_range': round(max(trend) - min(trend), 6),
        'detrended_mean': round(detrend_mean, 6)
    }
