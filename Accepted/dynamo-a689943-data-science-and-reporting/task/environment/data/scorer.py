"""Anomaly Scorer module for the anomaly detection pipeline.

Computes anomaly scores from whitened spectral residuals. The scoring
integrates frequency-domain evidence with time-domain deviation to
identify observations that are spectrally inconsistent with the
fitted AR model.

The score for each observation combines:
- Spectral residual energy (how much the observed spectrum deviates)
- Normalized by effective sample size for proper scaling
- Temporal decay weighting for recency emphasis
"""

import math
from typing import List, Dict, Tuple, Optional


class ScorerError(Exception):
    """Raised when anomaly scoring encounters an error."""
    pass


def compute_anomaly_scores(whitened_residuals: List[float],
                           n_effective: float,
                           decay_rate: float = 0.05
                           ) -> Dict[str, object]:
    """Compute anomaly scores from whitened spectral residuals.

    The score for each frequency bin is the whitened residual
    normalized by effective sample size. Higher n_effective means
    more statistical evidence, so scores are scaled inversely.

    Score_i = residual_i * (n / n_effective)

    Where the n/n_effective ratio accounts for the window's noise
    bandwidth. For rectangular windows (n_eff = n), this is unity.
    For tapered windows, n/n_eff > 1, amplifying scores appropriately
    because tapered windows have less effective data.

    Args:
        whitened_residuals: Whitened spectral residuals.
        n_effective: Effective sample size for normalization.
        decay_rate: Temporal decay rate for weighting.

    Returns:
        Dictionary with:
            'scores': per-frequency anomaly scores
            'mean_score': aggregate anomaly score
            'max_score': maximum frequency-band score
    """
    n = len(whitened_residuals)
    if n == 0:
        return {'scores': [], 'mean_score': 0.0, 'max_score': 0.0}

    if n_effective <= 0:
        raise ScorerError("Effective sample size must be positive")

    # Compute per-frequency scores with n_effective normalization
    # The normalization factor accounts for window energy: scores
    # are scaled by n/n_eff so that tapered windows produce properly
    # calibrated anomaly levels
    norm_factor = n / n_effective
    scores = []
    for residual in whitened_residuals:
        score = residual * norm_factor
        scores.append(score)

    # Apply temporal decay weighting
    from whitening import compute_temporal_decay_weights
    weights = compute_temporal_decay_weights(n, decay_rate)
    weighted_scores = [s * w for s, w in zip(scores, weights)]

    mean_score = sum(weighted_scores) / n
    max_score = max(weighted_scores) if weighted_scores else 0.0

    return {
        'scores': weighted_scores,
        'mean_score': mean_score,
        'max_score': max_score
    }


def compute_threshold(scores: List[float], confidence: float = 0.95
                      ) -> float:
    """Compute anomaly detection threshold from scores.

    Uses an empirical threshold based on the distribution of scores
    within the segment. The threshold is set at the specified quantile
    of the score distribution.

    For segment-local thresholding, this should be called separately
    for each segment's scores to account for varying noise levels.

    Args:
        scores: Anomaly scores for the segment.
        confidence: Confidence level for threshold (e.g., 0.95).

    Returns:
        Threshold value above which observations are anomalous.
    """
    if not scores:
        return 0.0

    n = len(scores)
    sorted_scores = sorted(scores)

    # Empirical quantile
    idx = min(int(confidence * n), n - 1)
    return sorted_scores[idx]


def classify_anomalies(scores: List[float], threshold: float
                       ) -> List[Dict[str, object]]:
    """Classify observations as anomalous or normal.

    Args:
        scores: Anomaly scores.
        threshold: Detection threshold.

    Returns:
        List of classification results with score and label.
    """
    results = []
    for i, score in enumerate(scores):
        is_anomaly = score > threshold
        results.append({
            'index': i,
            'score': round(score, 6),
            'threshold': round(threshold, 6),
            'is_anomaly': is_anomaly,
            'severity': round(score / threshold, 6) if threshold > 0 else 0.0
        })

    return results


def aggregate_segment_results(segment_results: List[List[Dict[str, object]]],
                              segment_offsets: List[int]
                              ) -> List[Dict[str, object]]:
    """Aggregate anomaly results from all segments into global indices.

    Maps segment-local indices back to global series positions.

    Args:
        segment_results: List of per-segment classification results.
        segment_offsets: Start index of each segment in the original series.

    Returns:
        Combined results with global indices.
    """
    global_results = []
    for seg_idx, (results, offset) in enumerate(zip(segment_results, segment_offsets)):
        for result in results:
            global_result = result.copy()
            global_result['global_index'] = result['index'] + offset
            global_result['segment'] = seg_idx
            global_results.append(global_result)

    # Sort by global index
    global_results.sort(key=lambda x: x['global_index'])
    return global_results
