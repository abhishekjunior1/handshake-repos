"""Segmenter module for the anomaly detection pipeline.

Implements variance-based change-point detection for segmenting
non-stationary time series into locally stationary regions. Each
segment is then analyzed independently for spectral anomalies.

The segmentation algorithm uses a sliding window variance ratio
test to identify points where the local variance changes significantly,
indicating a regime shift in the generating process.
"""

import math
from typing import List, Dict, Tuple, Optional


class SegmentationError(Exception):
    """Raised when segmentation encounters an error."""
    pass


def compute_local_variance(series: List[float], center: int,
                           half_window: int) -> float:
    """Compute local variance around a center point.

    Uses a symmetric window of size 2*half_window+1 centered at
    the given index, clipped to series boundaries.

    Args:
        series: Input time series.
        center: Center index for the local window.
        half_window: Half-width of the variance window.

    Returns:
        Local variance estimate.
    """
    n = len(series)
    start = max(0, center - half_window)
    end = min(n, center + half_window + 1)

    segment = series[start:end]
    m = len(segment)
    if m < 2:
        return 0.0

    mean_val = sum(segment) / m
    var = sum((x - mean_val) ** 2 for x in segment) / (m - 1)
    return var


def detect_change_points(series: List[float],
                         min_segment_length: int = 15,
                         variance_ratio_threshold: float = 2.5,
                         half_window: int = 8) -> List[int]:
    """Detect variance change points in the time series.

    Scans the series with a sliding window and identifies points
    where the ratio of forward/backward local variances exceeds
    the threshold, indicating a regime change.

    Args:
        series: Input time series.
        min_segment_length: Minimum observations between change points.
        variance_ratio_threshold: Threshold for variance ratio test.
        half_window: Half-width for local variance computation.

    Returns:
        List of change point indices (sorted).
    """
    n = len(series)
    if n < 2 * min_segment_length:
        return []  # Too short to segment

    change_points = []
    last_cp = 0

    for i in range(min_segment_length, n - min_segment_length):
        # Skip if too close to last change point
        if i - last_cp < min_segment_length:
            continue

        # Compute backward and forward local variances
        var_back = compute_local_variance(series, i - half_window // 2, half_window)
        var_fwd = compute_local_variance(series, i + half_window // 2, half_window)

        if var_back < 1e-12 and var_fwd < 1e-12:
            continue

        # Variance ratio (larger / smaller)
        if var_back < 1e-12:
            ratio = var_fwd / 1e-12
        elif var_fwd < 1e-12:
            ratio = var_back / 1e-12
        else:
            ratio = max(var_back / var_fwd, var_fwd / var_back)

        if ratio > variance_ratio_threshold:
            change_points.append(i)
            last_cp = i

    return change_points


def segment_series(series: List[float],
                   change_points: List[int]) -> List[Dict[str, object]]:
    """Split a time series into segments at the detected change points.

    Each segment is a dictionary containing the data slice and its
    position within the original series.

    Args:
        series: Input time series.
        change_points: Sorted list of change point indices.

    Returns:
        List of segment dictionaries with:
            'data': list of values in this segment
            'start': start index in original series
            'end': end index (exclusive) in original series
            'length': number of observations
    """
    n = len(series)
    segments = []

    boundaries = [0] + sorted(change_points) + [n]

    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        if end > start:
            segments.append({
                'data': series[start:end],
                'start': start,
                'end': end,
                'length': end - start
            })

    return segments


def compute_segment_statistics(segments: List[Dict[str, object]]
                               ) -> List[Dict[str, float]]:
    """Compute summary statistics for each segment.

    Args:
        segments: List of segment dictionaries.

    Returns:
        List of statistics dictionaries with mean, variance, etc.
    """
    stats = []
    for seg in segments:
        data = seg['data']
        n = len(data)
        if n == 0:
            stats.append({'mean': 0.0, 'variance': 0.0, 'std': 0.0, 'n': 0})
            continue

        mean_val = sum(data) / n
        if n > 1:
            var = sum((x - mean_val) ** 2 for x in data) / (n - 1)
        else:
            var = 0.0

        stats.append({
            'mean': mean_val,
            'variance': var,
            'std': math.sqrt(var),
            'n': n,
            'min': min(data),
            'max': max(data)
        })

    return stats


def validate_segmentation(segments: List[Dict[str, object]],
                          original_length: int) -> bool:
    """Validate that segments cover the entire original series.

    Checks for gaps and overlaps in the segmentation.

    Args:
        segments: List of segment dictionaries.
        original_length: Length of the original series.

    Returns:
        True if segmentation is valid (no gaps/overlaps).
    """
    if not segments:
        return original_length == 0

    # Check coverage
    total = sum(seg['length'] for seg in segments)
    if total != original_length:
        return False

    # Check ordering and adjacency
    for i in range(len(segments) - 1):
        if segments[i]['end'] != segments[i + 1]['start']:
            return False

    return segments[0]['start'] == 0 and segments[-1]['end'] == original_length
