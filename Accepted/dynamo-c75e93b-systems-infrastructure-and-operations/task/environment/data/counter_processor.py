"""
Counter processor module for the metrics aggregation pipeline.

Handles monotonically increasing counter metrics following Prometheus conventions:
- Detects counter resets (value decrease between consecutive samples)
- Applies wrap-around correction using the maximum counter width
- Computes deltas between consecutive samples accounting for resets
"""

from typing import Optional


# Standard counter widths for wrap-around correction
COUNTER_WIDTH_32 = 2**32
COUNTER_WIDTH_64 = 2**64

# Default assumes 64-bit counters (standard for modern Prometheus exporters)
DEFAULT_COUNTER_WIDTH = COUNTER_WIDTH_64


def detect_counter_reset(prev_value: float, curr_value: float) -> bool:
    """
    Detect a counter reset between two consecutive samples.
    A reset occurs when the current value is strictly less than the previous value.
    This follows the Prometheus counter reset convention.
    """
    return curr_value < prev_value


def compute_delta_with_reset_correction(
    prev_value: float,
    curr_value: float,
    counter_width: int = DEFAULT_COUNTER_WIDTH
) -> float:
    """
    Compute the delta between two consecutive counter samples,
    applying wrap-around correction if a reset is detected.

    For normal increments: delta = curr - prev
    For resets: delta = (counter_width - prev) + curr
    This assumes the counter wrapped around exactly once.
    """
    if detect_counter_reset(prev_value, curr_value):
        # Wrap-around correction: assume single wrap at counter_width
        delta = (counter_width - prev_value) + curr_value
    else:
        delta = curr_value - prev_value
    return delta


def compute_counter_deltas(
    datapoints: list[dict],
    counter_width: int = DEFAULT_COUNTER_WIDTH
) -> list[dict]:
    """
    Compute deltas for a sorted sequence of counter datapoints.
    Returns a list of delta records with timestamp and delta value.

    The first datapoint has no predecessor, so it is skipped.
    Each subsequent datapoint produces a delta relative to its predecessor,
    with wrap-around correction applied for detected resets.
    """
    if len(datapoints) < 2:
        return []

    deltas = []
    for i in range(1, len(datapoints)):
        prev_dp = datapoints[i - 1]
        curr_dp = datapoints[i]

        delta = compute_delta_with_reset_correction(
            prev_dp["value"],
            curr_dp["value"],
            counter_width
        )

        deltas.append({
            "timestamp": curr_dp["timestamp"],
            "prev_timestamp": prev_dp["timestamp"],
            "delta": delta,
            "reset_detected": detect_counter_reset(
                prev_dp["value"], curr_dp["value"]
            )
        })

    return deltas


def aggregate_counter_totals(
    counter_metrics: list[dict],
    counter_width: int = DEFAULT_COUNTER_WIDTH
) -> dict[str, dict]:
    """
    Aggregate counter metrics across all sources.
    For each counter name, compute the total accumulated delta
    and track reset events.

    Returns a dict mapping metric name to aggregated stats:
    {
        "total_delta": float,
        "num_resets": int,
        "num_samples": int,
        "sources": list[str]
    }
    """
    aggregated: dict[str, dict] = {}

    for metric in counter_metrics:
        name = metric["name"]
        source = metric["source"]
        datapoints = sorted(metric["datapoints"], key=lambda dp: dp["timestamp"])

        deltas = compute_counter_deltas(datapoints, counter_width)

        if name not in aggregated:
            aggregated[name] = {
                "total_delta": 0.0,
                "num_resets": 0,
                "num_samples": 0,
                "sources": []
            }

        total_delta = sum(d["delta"] for d in deltas)
        num_resets = sum(1 for d in deltas if d["reset_detected"])

        aggregated[name]["total_delta"] += total_delta
        aggregated[name]["num_resets"] += num_resets
        aggregated[name]["num_samples"] += len(datapoints)
        aggregated[name]["sources"].append(source)

    return aggregated


def compute_per_second_rate(delta: float, time_delta_sec: float) -> float:
    """
    Compute the per-second rate from a counter delta and time interval.
    This is the standard Prometheus rate() computation.

    rate = delta / time_interval_seconds

    Returns 0.0 if time_delta is zero or negative to avoid division errors.
    """
    if time_delta_sec <= 0:
        return 0.0
    return delta / time_delta_sec


def compute_rates_from_deltas(deltas: list[dict]) -> list[dict]:
    """
    Convert counter deltas to per-second rates using the time interval
    between consecutive samples.

    Each delta record must have 'timestamp', 'prev_timestamp', and 'delta' fields.
    Returns rate records with timestamp and per-second rate value.
    """
    rates = []
    for delta_record in deltas:
        time_delta = delta_record["timestamp"] - delta_record["prev_timestamp"]
        rate = compute_per_second_rate(delta_record["delta"], time_delta)
        rates.append({
            "timestamp": delta_record["timestamp"],
            "rate_per_sec": rate,
            "time_delta_sec": time_delta,
            "raw_delta": delta_record["delta"]
        })
    return rates
