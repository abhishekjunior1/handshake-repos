"""
Confidence Scorer Module
Computes confidence scores for test classifications based on signal strength,
consistency across windows, and sample size adequacy.
"""

import math


def score_classifications(classifications, flakiness_metrics, cumulative_rates,
                          timing_stats, config):
    """
    Assign confidence scores to each classification.

    Args:
        classifications: List of classification dicts from classifier module.
        flakiness_metrics: Dict mapping test_id -> flakiness analysis results.
        cumulative_rates: Dict mapping test_id -> long-term cumulative failure rate.
        timing_stats: Dict mapping test_id -> timing statistics.
        config: Pipeline config with confidence method.

    Returns:
        List of classification dicts with added "confidence" field.
    """
    method = config.get("confidence_method", "harmonic")
    scored = []

    for classification in classifications:
        tid = classification["test_id"]
        category = classification["category"]

        flaky_data = flakiness_metrics.get(tid, {})
        cum_rate = cumulative_rates.get(tid, 0.0)
        timing = timing_stats.get(tid, {})

        signals = _compute_confidence_signals(category, classification, flaky_data,
                                              cum_rate, timing)

        confidence = _combine_signals(signals, method)
        entry = dict(classification)
        entry["confidence"] = round(confidence, 4)
        scored.append(entry)

    return scored


def _compute_confidence_signals(category, classification, flaky_data, cumulative_rate,
                                 timing):
    """
    Compute individual confidence signals based on the assigned category.
    Each signal is in [0, 1] where 1 = very confident.
    """
    signals = []

    if category == "deterministic_bug":
        # High cumulative rate → high confidence in deterministic classification
        rate_signal = min(cumulative_rate / 1.0, 1.0)
        signals.append(rate_signal)

        # Consistency: low flip rate → more confident it's deterministic (not flaky)
        flip_rate = flaky_data.get("flip_rate", 0.0)
        consistency_signal = 1.0 - min(flip_rate * 2, 1.0)
        signals.append(consistency_signal)

        # Sample size signal
        sample_signal = _sample_adequacy(flaky_data)
        signals.append(sample_signal)

    elif category == "flaky":
        # Flip rate strength — higher flip rate = more confident it's flaky
        flip_rate = flaky_data.get("flip_rate", 0.0)
        flip_signal = min(flip_rate / 0.5, 1.0)
        signals.append(flip_signal)

        # Rate variance across windows
        rates = flaky_data.get("windowed_rates", [])
        if len(rates) > 1:
            rate_mean = sum(rates) / len(rates)
            variance = sum((r - rate_mean) ** 2 for r in rates) / len(rates)
            variance_signal = min(math.sqrt(variance) * 3, 1.0)
        else:
            variance_signal = 0.5
        signals.append(variance_signal)

        # Timing instability
        cv = timing.get("cv", 0.0)
        timing_signal = min(cv / 0.5, 1.0)
        signals.append(timing_signal)

    elif category == "environment_dependent":
        # Environment correlation strength
        metrics = classification.get("metrics", {})
        # Use failure rate as proxy for env correlation strength
        rate = metrics.get("failure_rate", 0.0)
        env_signal = min(rate * 2, 1.0)
        signals.append(env_signal)

        # Sample adequacy
        sample_signal = _sample_adequacy(flaky_data)
        signals.append(sample_signal)

        signals.append(0.8)  # Prior confidence for env classification

    else:  # healthy
        # High confidence if truly no failures
        rate = classification.get("metrics", {}).get("failure_rate", 0.0)
        no_fail_signal = 1.0 - rate
        signals.append(no_fail_signal)

        # Stable trend
        trend = flaky_data.get("trend", "stable")
        trend_signal = 1.0 if trend == "stable" else 0.6
        signals.append(trend_signal)

        signals.append(0.95)  # Prior confidence for healthy

    return signals


def _combine_signals(signals, method):
    """
    Combine confidence signals using the specified method.
    Harmonic mean prevents a single high signal from dominating.
    """
    if not signals:
        return 0.5

    # Filter out zero signals to avoid division by zero in harmonic mean
    filtered = [max(s, 0.01) for s in signals]

    if method == "harmonic":
        return _harmonic_mean(filtered)
    else:
        return sum(filtered) / len(filtered)


def _harmonic_mean(values):
    """
    Compute harmonic mean of a list of values.
    Harmonic mean is appropriate when signals should ALL be strong —
    a single weak signal pulls the mean down significantly.
    """
    if not values:
        return 0.0

    n = len(values)
    reciprocal_sum = sum(1.0 / v for v in values)

    if reciprocal_sum == 0:
        return 0.0

    return n / reciprocal_sum


def _sample_adequacy(flaky_data):
    """
    Compute sample size adequacy signal.
    More runs → more confidence in classification.
    """
    rates = flaky_data.get("windowed_rates", [])
    total_observations = sum(1 for _ in rates)

    # Assume each window has meaningful data; more windows = better
    if total_observations >= 5:
        return 1.0
    elif total_observations >= 3:
        return 0.8
    elif total_observations >= 1:
        return 0.6
    else:
        return 0.3
