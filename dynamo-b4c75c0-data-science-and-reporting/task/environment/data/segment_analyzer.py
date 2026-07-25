"""
Time series segmentation for non-stationarity handling.

Segments a time series into approximately stationary sub-intervals for
local spectral analysis. Uses a simple variance-based change detection
approach: if the running variance differs significantly from the segment's
accumulated variance, a new segment boundary is declared.

For stationary series (no significant variance changes), the entire series
is returned as a single segment. The anomaly detection pipeline uses
per-segment statistics and thresholds for more sensitive detection.
"""

import math


def segment_series(series, min_length):
    """Segment series into approximately stationary sub-intervals.

    Uses cumulative variance monitoring to detect structural breaks
    in the variance level. Returns segment boundaries as (start, end)
    tuples where segments are non-overlapping and cover the full series.

    For series with constant variance (stationary), returns a single
    segment covering the entire series.

    Args:
        series: Time series values
        min_length: Minimum segment length (prevents over-segmentation)

    Returns:
        List of (start_index, end_index) tuples
    """
    n = len(series)
    if n < 2 * min_length:
        return [(0, n)]

    boundaries = [0]
    segment_start = 0

    # Running statistics for change detection
    running_mean = series[0]
    running_m2 = 0.0  # Running sum of squared deviations (Welford's)
    count = 1

    for i in range(1, n):
        count += 1
        delta = series[i] - running_mean
        running_mean += delta / count
        delta2 = series[i] - running_mean
        running_m2 += delta * delta2

        # Check for variance change every min_length observations
        if count >= 2 * min_length and (i - segment_start) >= min_length:
            # Compute variance of first half vs second half
            mid = segment_start + (i - segment_start) // 2
            first_half = series[segment_start:mid]
            second_half = series[mid:i + 1]

            var1 = _compute_variance(first_half)
            var2 = _compute_variance(second_half)

            # F-test approximation for variance equality
            if var1 > 0 and var2 > 0:
                f_ratio = max(var1, var2) / min(var1, var2)
                # Use a conservative threshold (3.0) for segmentation
                if f_ratio > 3.0 and (i - segment_start) >= 2 * min_length:
                    # New segment boundary
                    boundaries.append(mid)
                    segment_start = mid
                    # Reset running stats
                    count = i - mid + 1
                    running_mean = sum(series[mid:i + 1]) / count
                    running_m2 = sum((x - running_mean) ** 2 for x in series[mid:i + 1])

    # Convert boundaries to (start, end) segments
    segments = []
    for i in range(len(boundaries)):
        start = boundaries[i]
        end = boundaries[i + 1] if i + 1 < len(boundaries) else n
        segments.append((start, end))

    return segments


def _compute_variance(data):
    """Compute population variance of a data list.

    Args:
        data: List of numeric values

    Returns:
        Population variance
    """
    n = len(data)
    if n < 2:
        return 0.0
    mean = sum(data) / n
    return sum((x - mean) ** 2 for x in data) / n


def compute_segment_statistics(series, segments):
    """Compute descriptive statistics for each segment.

    Provides per-segment mean, variance, range, and length for
    diagnostic reporting and segment-level threshold computation.

    Args:
        series: Full time series
        segments: List of (start, end) segment boundaries

    Returns:
        List of dictionaries with segment statistics
    """
    stats = []
    for start, end in segments:
        segment = series[start:end]
        n = len(segment)

        if n == 0:
            stats.append({
                'start': start, 'end': end, 'n': 0,
                'mean': 0.0, 'variance': 0.0,
                'min': 0.0, 'max': 0.0
            })
            continue

        seg_mean = sum(segment) / n
        seg_var = sum((x - seg_mean) ** 2 for x in segment) / n

        stats.append({
            'start': start,
            'end': end,
            'n': n,
            'mean': seg_mean,
            'variance': seg_var,
            'min': min(segment),
            'max': max(segment)
        })

    return stats
