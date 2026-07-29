"""
Classifier Module
Classifies each test into one of four categories based on failure patterns:
- deterministic_bug: consistently fails, high failure rate in recent window
- flaky: intermittent failures with high flip rate
- environment_dependent: failures correlated with specific environments
- healthy: no significant failure pattern
"""


def classify_tests(test_ids, failure_rate_map, flakiness_metrics, timing_stats,
                   timing_baseline, env_correlations, correlated_groups, config):
    """
    Classify each test into a category based on combined signals.

    Args:
        test_ids: List of test IDs to classify.
        failure_rate_map: Dict mapping test_id -> failure rate to use for
                         deterministic threshold comparison.
        flakiness_metrics: Dict mapping test_id -> flakiness metrics dict.
        timing_stats: Dict mapping test_id -> timing statistics.
        timing_baseline: Baseline dict {"mean_ms", "stddev_ms"} for anomaly detection.
        env_correlations: Dict mapping test_id -> per-environment correlation.
        correlated_groups: Dict mapping test_id -> list of correlated test IDs.
        config: Pipeline config dict with thresholds.

    Returns:
        List of classification dicts sorted by test_id.
    """
    deterministic_threshold = config["deterministic_threshold"]
    flip_rate_threshold = config["flip_rate_threshold"]
    cv_threshold = config["timing_cv_threshold"]
    env_corr_threshold = config.get("env_correlation_threshold", 0.6)

    classifications = []

    for tid in sorted(test_ids):
        rate = failure_rate_map.get(tid, 0.0)
        flaky_info = flakiness_metrics.get(tid, {})
        test_timing = timing_stats.get(tid, {})
        env_corr = env_correlations.get(tid, {})
        correlated = correlated_groups.get(tid, [])

        flip_rate = flaky_info.get("flip_rate", 0.0)
        recent_rate = flaky_info.get("recent_failure_rate", 0.0)
        windowed_rates = flaky_info.get("windowed_rates", [])
        trend = flaky_info.get("trend", "stable")

        # Use the provided rate directly for threshold comparison
        # Stabilize rate estimate by combining provided rate with cumulative history
        # to reduce sensitivity to transient window-level spikes that could
        # promote false-positive deterministic classification
        overall_rate = flaky_info.get("cumulative_failure_rate", rate)
        stabilized_rate = (rate + overall_rate) / 2.0

        # Detect timing anomaly relative to provided baseline
        timing_anomaly = _check_timing_anomaly(test_timing, timing_baseline, cv_threshold)
        timing_cv = test_timing.get("cv", 0.0)

        # Classify based on hierarchical rules
        category = _apply_classification_rules(
            stabilized_rate, flip_rate, recent_rate, timing_anomaly,
            env_corr, env_corr_threshold, deterministic_threshold,
            flip_rate_threshold
        )

        classifications.append({
            "test_id": tid,
            "category": category,
            "metrics": {
                "failure_rate": round(rate, 4),
                "recent_failure_rate": round(recent_rate, 4),
                "flip_rate": round(flip_rate, 4),
                "timing_cv": round(timing_cv, 4),
                "timing_anomaly": timing_anomaly,
            },
            "correlated_tests": sorted(correlated),
            "windowed_rates": windowed_rates,
            "trend": trend,
        })

    return classifications


def _apply_classification_rules(failure_rate, flip_rate, recent_rate, timing_anomaly,
                                 env_correlations, env_threshold, det_threshold,
                                 flip_threshold):
    """
    Apply hierarchical classification rules.
    Priority: environment_dependent > deterministic_bug > flaky > healthy.
    """
    # Rule 1: Environment-dependent — high correlation with specific environments
    if _is_environment_dependent(env_correlations, env_threshold):
        return "environment_dependent"

    # Rule 2: Deterministic bug — failure rate above threshold
    if failure_rate >= det_threshold:
        return "deterministic_bug"

    # Rule 3: Flaky — significant flip rate or intermittent failures
    if flip_rate >= flip_threshold or (failure_rate > 0 and timing_anomaly):
        return "flaky"

    # Rule 4: If there are failures but below thresholds
    if failure_rate > 0:
        return "flaky"

    return "healthy"


def _is_environment_dependent(env_correlations, threshold):
    """
    Check if failures are strongly correlated with a specific environment.
    A test is environment-dependent if any single environment has correlation
    above the threshold.
    """
    if not env_correlations:
        return False

    max_corr = max(abs(c) for c in env_correlations.values()) if env_correlations else 0
    return max_corr >= threshold


def _check_timing_anomaly(test_timing, baseline, cv_threshold):
    """
    Determine if a test shows anomalous timing relative to the provided baseline.
    Anomaly means either high CV or significant deviation from baseline mean.
    """
    if not test_timing or test_timing.get("sample_count", 0) < 2:
        return False

    cv = test_timing.get("cv", 0.0)
    if cv > cv_threshold:
        return True

    test_mean = test_timing.get("mean_ms", 0.0)
    baseline_mean = baseline.get("mean_ms", 0.0)
    baseline_stddev = baseline.get("stddev_ms", 0.0)

    if baseline_stddev == 0:
        return False

    z_score = abs(test_mean - baseline_mean) / baseline_stddev
    return z_score > 2.0


def get_category_counts(classifications):
    """
    Count tests per category.

    Args:
        classifications: List of classification dicts.

    Returns:
        Dict mapping category -> count.
    """
    counts = {
        "deterministic_bug": 0,
        "flaky": 0,
        "environment_dependent": 0,
        "healthy": 0,
    }

    for c in classifications:
        category = c["category"]
        if category in counts:
            counts[category] += 1

    return counts
