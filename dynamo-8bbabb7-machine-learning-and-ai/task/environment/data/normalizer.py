"""
Feature normalization for sensor signal features.

Normalizes extracted features against a reference baseline using z-score
normalization: (x - baseline_mean) / baseline_std.

The baseline represents "normal operating conditions" — features from
a healthy/known-good state. Normalized features then indicate how many
standard deviations the current observation deviates from normal.

The caller provides either pre-computed baseline statistics (from a
reference dataset) or the normalizer computes them from the current
feature vector (for self-relative normalization).
"""

import math


def compute_baseline_stats(feature_vector):
    """Compute baseline statistics from a feature vector.

    Computes mean and std across all feature values. This provides
    a self-relative baseline when no external reference is available.

    Args:
        feature_vector: Dictionary mapping feature names to values

    Returns:
        Dictionary with 'mean' and 'std' for the feature set
    """
    values = list(feature_vector.values())
    n = len(values)

    if n == 0:
        return {'mean': 0.0, 'std': 1.0}

    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    std = math.sqrt(variance) if variance > 0 else 1.0

    return {'mean': mean, 'std': std}


def normalize_features(feature_vector, baseline_stats):
    """Normalize features using baseline statistics.

    Applies z-score normalization: (x - mean) / std

    If baseline_stats contains per-feature statistics (dict of dicts),
    uses per-feature normalization. Otherwise uses global statistics.

    Args:
        feature_vector: Dictionary mapping feature names to raw values
        baseline_stats: Dictionary with normalization parameters

    Returns:
        Dictionary mapping feature names to normalized values
    """
    normalized = {}

    if 'mean' in baseline_stats and 'std' in baseline_stats:
        # Global normalization (single mean/std for all features)
        mean = baseline_stats['mean']
        std = baseline_stats['std']
        if std < 1e-15:
            std = 1.0

        for name, value in feature_vector.items():
            normalized[name] = (value - mean) / std
    else:
        # Per-feature normalization
        for name, value in feature_vector.items():
            if name in baseline_stats:
                stats = baseline_stats[name]
                mean = stats.get('mean', 0.0)
                std = stats.get('std', 1.0)
                if std < 1e-15:
                    std = 1.0
                normalized[name] = (value - mean) / std
            else:
                normalized[name] = value

    return normalized


def compute_deviation_score(normalized_features):
    """Compute overall deviation score from normalized features.

    Returns the L2 norm of the normalized feature vector, representing
    the total deviation from baseline conditions.

    Args:
        normalized_features: Dictionary of normalized feature values

    Returns:
        Scalar deviation score (float >= 0)
    """
    values = list(normalized_features.values())
    if not values:
        return 0.0

    return math.sqrt(sum(v ** 2 for v in values) / len(values))
