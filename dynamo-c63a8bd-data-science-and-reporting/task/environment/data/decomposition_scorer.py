"""
Decomposition quality scoring and segment-level assessment.

Evaluates the harmonic decomposition quality for each detected
stationarity segment and computes per-segment thresholds for
anomaly detection in the residual series.
"""

import math


def compute_segment_scores(series, residuals, segments, threshold_percentile):
    """Compute per-segment decomposition quality scores.

    For each segment, assesses how well the harmonic model
    captures the local signal structure by comparing harmonic
    energy to residual energy within that segment.

    Args:
        series: Original time series.
        residuals: Residual after harmonic + trend removal.
        segments: List of (start, end) segment boundaries.
        threshold_percentile: Percentile for anomaly threshold.

    Returns:
        List of segment score dictionaries.
    """
    segment_scores = []

    for start, end in segments:
        seg_series = series[start:end]
        seg_residuals = residuals[start:end]
        seg_n = end - start

        if seg_n < 3:
            segment_scores.append(_empty_segment_score(start, end))
            continue

        # Segment statistics
        seg_mean = sum(seg_series) / seg_n
        seg_var = sum((x - seg_mean) ** 2 for x in seg_series) / seg_n

        res_mean = sum(seg_residuals) / seg_n
        res_var = sum((r - res_mean) ** 2 for r in seg_residuals) / seg_n

        # Variance ratio: residual/signal
        if seg_var > 0:
            var_ratio = res_var / seg_var
        else:
            var_ratio = 1.0

        # Segment-specific anomaly threshold
        threshold = compute_segment_threshold(seg_residuals, threshold_percentile)

        # Count anomalies in this segment
        anomaly_indices = [i + start for i, r in enumerate(seg_residuals)
                          if abs(r) > threshold]

        segment_scores.append({
            'start': start,
            'end': end,
            'length': seg_n,
            'signal_variance': round(seg_var, 6),
            'residual_variance': round(res_var, 6),
            'variance_ratio': round(var_ratio, 6),
            'threshold': round(threshold, 6),
            'n_anomalies': len(anomaly_indices),
            'anomaly_indices': anomaly_indices
        })

    return segment_scores


def compute_segment_threshold(residuals, percentile):
    """Compute anomaly threshold for a segment based on residual distribution.

    Uses the specified percentile of |residual| values as the threshold.
    Observations exceeding this threshold are flagged as anomalous
    (the decomposition could not explain them).

    Args:
        residuals: Segment residual values.
        percentile: Threshold percentile (0-100).

    Returns:
        Anomaly threshold value.
    """
    n = len(residuals)
    if n < 2:
        return float('inf')

    abs_residuals = sorted(abs(r) for r in residuals)

    # Percentile computation (linear interpolation)
    idx = (percentile / 100.0) * (n - 1)
    lower = int(math.floor(idx))
    upper = min(lower + 1, n - 1)
    frac = idx - lower

    threshold = abs_residuals[lower] * (1 - frac) + abs_residuals[upper] * frac

    return threshold


def compute_global_threshold(series, percentile):
    """Compute a global anomaly threshold from the full series.

    Uses the specified percentile of absolute deviations from mean
    as a series-wide threshold.

    Args:
        series: Full time series.
        percentile: Threshold percentile.

    Returns:
        Global threshold value.
    """
    n = len(series)
    mean = sum(series) / n
    abs_devs = sorted(abs(x - mean) for x in series)

    idx = (percentile / 100.0) * (n - 1)
    lower = int(math.floor(idx))
    upper = min(lower + 1, n - 1)
    frac = idx - lower

    return abs_devs[lower] * (1 - frac) + abs_devs[upper] * frac


def detect_segments(series, min_segment_length):
    """Detect stationarity segments using variance-ratio test.

    Splits the series at points where the local variance changes
    significantly, creating segments within which the process
    is approximately stationary.

    Args:
        series: Input time series.
        min_segment_length: Minimum observations per segment.

    Returns:
        List of (start, end) tuples defining segments.
    """
    n = len(series)
    if n < 2 * min_segment_length:
        return [(0, n)]

    # Sliding variance ratio test
    half_window = min_segment_length
    change_points = []

    for t in range(half_window, n - half_window):
        left = series[t - half_window:t]
        right = series[t:t + half_window]

        left_var = sum((x - sum(left) / len(left)) ** 2 for x in left) / len(left)
        right_var = sum((x - sum(right) / len(right)) ** 2 for x in right) / len(right)

        if left_var > 0 and right_var > 0:
            ratio = max(left_var, right_var) / min(left_var, right_var)
            if ratio > 4.0:  # F-test critical value approximation
                if not change_points or t - change_points[-1] >= min_segment_length:
                    change_points.append(t)

    # Build segments
    segments = []
    prev = 0
    for cp in change_points:
        segments.append((prev, cp))
        prev = cp
    segments.append((prev, n))

    return segments


def _empty_segment_score(start, end):
    """Return empty score for degenerate segment."""
    return {
        'start': start,
        'end': end,
        'length': end - start,
        'signal_variance': 0.0,
        'residual_variance': 0.0,
        'variance_ratio': 1.0,
        'threshold': 0.0,
        'n_anomalies': 0,
        'anomaly_indices': []
    }
