"""
Anomaly scoring for time series observations using spectral residuals.

Scores each observation based on its contribution to unexplained spectral
energy. Observations that strongly contribute to frequency components where
the actual spectrum exceeds the fitted envelope receive higher anomaly scores.

The scoring uses a projection approach: each observation's contribution to
each frequency bin is computed, then weighted by the spectral residual at
that bin. The result is a per-observation anomaly score in [0, inf) that
is later clipped to [0, 1] by the pipeline for aggregation.

The threshold computation uses percentile-based cutoffs, supporting both
global (full-series) and segment-level thresholds for non-stationary series.
"""

import math


def score_observations(data, spectral_residuals, normalization_n):
    """Score each observation for spectral anomalousness.

    For each observation x_t, computes how much it contributes to
    anomalous (excess) spectral energy across all frequency bins:

        score(t) = sum_k max(0, resid_k) * |cos(2*pi*f_k*t)| / Z

    where Z is a normalization constant based on the series length.

    The scoring function is agnostic to what data it receives — it scores
    whatever series is passed. The caller is responsible for passing the
    appropriate input (whitened residuals for proper anomaly detection).

    Args:
        data: Series to score (should be whitened residuals)
        spectral_residuals: Log-ratio spectral residuals
        normalization_n: Normalization denominator for density computation

    Returns:
        List of anomaly scores (one per observation)
    """
    n = len(data)
    n_bins = len(spectral_residuals)

    if n == 0 or n_bins == 0:
        return [0.0] * n

    # Only consider positive residuals (excess spectral energy = anomalous)
    positive_residuals = [max(0.0, r) for r in spectral_residuals]
    total_excess = sum(positive_residuals)

    if total_excess < 1e-10:
        return [0.0] * n

    # Normalization factor based on series length
    norm_factor = math.sqrt(normalization_n) if normalization_n > 0 else 1.0

    scores = []
    for t in range(n):
        score = 0.0
        for k in range(n_bins):
            freq = (k + 1) / (2 * n_bins)
            # Observation's frequency contribution
            contribution = abs(math.cos(2 * math.pi * freq * t))
            # Weight by excess spectral energy at this bin
            score += positive_residuals[k] * contribution

        # Normalize by total excess energy and scale factor
        score = score / (total_excess * norm_factor) * abs(data[t])
        scores.append(score)

    return scores


def compute_threshold(series, percentile):
    """Compute anomaly score threshold from a reference series.

    Uses the specified percentile of the absolute values as the
    threshold. Observations with scores above this are classified
    as anomalous.

    This function computes a GLOBAL threshold from the full series.
    For segment-specific thresholds, call with individual segments.

    Args:
        series: Reference data (full series or segment)
        percentile: Percentile for threshold (0-100)

    Returns:
        Threshold value (float)
    """
    if not series:
        return 0.0

    # Compute percentile of absolute values
    abs_values = sorted(abs(x) for x in series)
    n = len(abs_values)

    # Linear interpolation for percentile
    rank = (percentile / 100.0) * (n - 1)
    lower_idx = int(math.floor(rank))
    upper_idx = min(lower_idx + 1, n - 1)
    fraction = rank - lower_idx

    threshold = abs_values[lower_idx] * (1 - fraction) + abs_values[upper_idx] * fraction

    # Convert to score scale (normalize by series std)
    std = math.sqrt(sum(x ** 2 for x in series) / n) if n > 0 else 1.0
    if std > 0:
        threshold = threshold / std

    return threshold


def compute_segment_threshold(segment, percentile, segment_variance):
    """Compute segment-specific anomaly threshold.

    Uses segment-local statistics for threshold computation, accounting
    for the segment's own variance level. This provides more sensitive
    detection in low-variance segments and prevents false positives in
    high-variance segments.

    Args:
        segment: Segment data values
        percentile: Percentile for threshold
        segment_variance: Pre-computed segment variance

    Returns:
        Segment-specific threshold
    """
    if not segment or segment_variance <= 0:
        return compute_threshold(segment, percentile)

    n = len(segment)
    abs_values = sorted(abs(x) for x in segment)

    # Percentile computation
    rank = (percentile / 100.0) * (n - 1)
    lower_idx = int(math.floor(rank))
    upper_idx = min(lower_idx + 1, n - 1)
    fraction = rank - lower_idx

    raw_threshold = abs_values[lower_idx] * (1 - fraction) + abs_values[upper_idx] * fraction

    # Normalize by segment standard deviation
    seg_std = math.sqrt(segment_variance)
    threshold = raw_threshold / seg_std if seg_std > 0 else raw_threshold

    return threshold
