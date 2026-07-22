"""
Rate computer module for the metrics aggregation pipeline.

Computes instantaneous and windowed rates from counter deltas.
Supports configurable rate windows, rate smoothing via exponential
moving averages, and rate-of-change (acceleration) detection.
"""

from typing import Optional


def compute_instantaneous_rate(delta: float, time_interval_sec: float) -> float:
    """
    Compute the instantaneous per-second rate.
    rate = counter_delta / time_interval

    This is the fundamental rate computation used by Prometheus rate().
    Returns 0.0 for zero or negative intervals.
    """
    if time_interval_sec <= 0.0:
        return 0.0
    return delta / time_interval_sec


def compute_windowed_rate(
    deltas: list[dict],
    window_size_sec: float
) -> list[dict]:
    """
    Compute the average rate over a sliding window.
    The window spans the most recent window_size_sec seconds of deltas.

    For each point, accumulates deltas within the window and divides
    by the window duration to get a smoothed rate.
    """
    if not deltas:
        return []

    rates = []
    for i, current in enumerate(deltas):
        window_start = current["timestamp"] - window_size_sec
        window_deltas = []
        window_time = 0.0

        # Look back through previous deltas within window
        for j in range(i, -1, -1):
            if deltas[j]["timestamp"] < window_start:
                break
            window_deltas.append(deltas[j])
            if j > 0:
                window_time += deltas[j]["timestamp"] - deltas[j]["prev_timestamp"]

        total_delta = sum(d["delta"] for d in window_deltas)
        # Use actual time span covered by window deltas
        if window_time > 0:
            rate = total_delta / window_time
        else:
            rate = 0.0

        rates.append({
            "timestamp": current["timestamp"],
            "rate_per_sec": rate,
            "window_samples": len(window_deltas),
            "window_duration_sec": window_time
        })

    return rates


def apply_exponential_smoothing(
    rates: list[dict],
    alpha: float = 0.3
) -> list[dict]:
    """
    Apply exponential moving average smoothing to a rate series.
    EMA_t = alpha * rate_t + (1 - alpha) * EMA_{t-1}

    Alpha controls responsiveness: higher alpha = more responsive.
    """
    if not rates:
        return []

    smoothed = []
    prev_ema = rates[0]["rate_per_sec"]

    for rate_record in rates:
        current_rate = rate_record["rate_per_sec"]
        ema = alpha * current_rate + (1 - alpha) * prev_ema
        smoothed.append({
            "timestamp": rate_record["timestamp"],
            "rate_per_sec": ema,
            "raw_rate": current_rate
        })
        prev_ema = ema

    return smoothed


def detect_rate_anomalies(
    rates: list[dict],
    threshold_multiplier: float = 3.0
) -> list[dict]:
    """
    Detect rate anomalies using a simple z-score approach.
    Points where rate exceeds mean ± threshold_multiplier * stddev
    are flagged as anomalies.
    """
    if len(rates) < 2:
        return []

    values = [r["rate_per_sec"] for r in rates]
    mean_rate = sum(values) / len(values)
    variance = sum((v - mean_rate) ** 2 for v in values) / len(values)
    stddev = variance ** 0.5

    if stddev == 0:
        return []

    anomalies = []
    for rate_record in rates:
        z_score = (rate_record["rate_per_sec"] - mean_rate) / stddev
        if abs(z_score) > threshold_multiplier:
            anomalies.append({
                "timestamp": rate_record["timestamp"],
                "rate_per_sec": rate_record["rate_per_sec"],
                "z_score": z_score,
                "anomaly_type": "spike" if z_score > 0 else "drop"
            })

    return anomalies


def compute_rate_of_change(rates: list[dict]) -> list[dict]:
    """
    Compute the rate of change (acceleration/deceleration) of the rate series.
    This is the second derivative: d(rate)/dt.
    """
    if len(rates) < 2:
        return []

    roc = []
    for i in range(1, len(rates)):
        prev = rates[i - 1]
        curr = rates[i]
        time_delta = curr["timestamp"] - prev["timestamp"]
        if time_delta > 0:
            acceleration = (curr["rate_per_sec"] - prev["rate_per_sec"]) / time_delta
        else:
            acceleration = 0.0

        roc.append({
            "timestamp": curr["timestamp"],
            "acceleration": acceleration,
            "rate_per_sec": curr["rate_per_sec"]
        })

    return roc
