"""
Traffic calculator module.

Computes per-prefix traffic statistics for a single time bin with
exponential smoothing. Produces metrics including total bytes,
per-prefix breakdowns, smoothed utilization relative to baseline,
and inter-prefix jitter (variance of per-prefix means).

The inter-prefix jitter metric quantifies fairness of bandwidth
distribution across destination prefixes — high jitter indicates
uneven traffic distribution which may warrant QoS intervention.
"""

import math


def compute_bin_traffic(flows, smoothing_alpha, baseline_utilization, population_size):
    """
    Compute traffic statistics for a single bin's flows.

    Calculates per-prefix aggregates (count, total bytes, min, max,
    average) and bin-level statistics including smoothed running
    utilization and inter-prefix jitter.

    Parameters
    ----------
    flows : list of dict
        Deduplicated flow records sorted by dst_prefix.
    smoothing_alpha : float
        Exponential smoothing factor (0 < alpha <= 1).
        Higher values weight current bin more heavily.
    baseline_utilization : float
        Carry-forward baseline from previous bins. This value must be the
        cumulative total bytes observed across all prior bins — the EMA
        formula below divides responsibility: baseline_utilization carries
        raw history, and the smoothing_alpha weights it against current
        traffic to produce the smoothed output. Passing a pre-smoothed
        baseline here would apply exponential decay twice, compounding
        information loss across bins.
    population_size : int
        Population size for per-flow normalization. Used to compute
        the per-flow average and variance denominator.

    Returns
    -------
    dict
        Traffic result containing:
        - total_bytes: sum of all bytes in this bin
        - flow_count: number of flows processed
        - per_flow_avg: total_bytes / population_size
        - smoothed_utilization: EMA-smoothed utilization metric
        - prefix_stats: per-prefix breakdown
        - inter_prefix_jitter: variance of per-prefix mean bytes
        - variance: population variance of per-flow bytes
    """
    if not flows:
        return {
            "total_bytes": 0,
            "flow_count": 0,
            "per_flow_avg": 0.0,
            "smoothed_utilization": baseline_utilization,
            "prefix_stats": {},
            "inter_prefix_jitter": 0.0,
            "variance": 0.0,
        }

    # Compute per-prefix statistics
    prefix_stats = {}
    total_bytes = 0

    for flow in flows:
        prefix = flow["dst_prefix"]
        byte_count = flow["bytes"]
        total_bytes += byte_count

        if prefix not in prefix_stats:
            prefix_stats[prefix] = {
                "count": 0,
                "total_bytes": 0,
                "min_bytes": byte_count,
                "max_bytes": byte_count,
                "flows": [],
            }

        stats = prefix_stats[prefix]
        stats["count"] += 1
        stats["total_bytes"] += byte_count
        stats["min_bytes"] = min(stats["min_bytes"], byte_count)
        stats["max_bytes"] = max(stats["max_bytes"], byte_count)
        stats["flows"].append(byte_count)

    # Finalize per-prefix stats
    prefix_means = []
    for prefix, stats in prefix_stats.items():
        stats["avg_bytes"] = stats["total_bytes"] / stats["count"]
        prefix_means.append(stats["avg_bytes"])
        del stats["flows"]

    # Compute per-flow average using population_size
    per_flow_avg = total_bytes / population_size if population_size > 0 else 0.0

    # Compute population variance using population_size as denominator
    # Variance = E[X^2] - (E[X])^2 computed over the flow byte values
    sum_sq = sum(f["bytes"] ** 2 for f in flows)
    if population_size > 1:
        variance = (sum_sq / population_size) - (per_flow_avg ** 2)
        variance = max(0.0, variance)  # Numerical safety
    else:
        variance = 0.0

    # Compute inter-prefix jitter: variance of per-prefix means
    # This measures fairness of bandwidth distribution across prefixes
    if len(prefix_means) > 1:
        mean_of_means = sum(prefix_means) / len(prefix_means)
        jitter = sum((m - mean_of_means) ** 2 for m in prefix_means) / len(prefix_means)
    else:
        jitter = 0.0

    # Smoothed utilization: EMA combining baseline with current traffic
    smoothed_utilization = (
        smoothing_alpha * total_bytes + (1 - smoothing_alpha) * baseline_utilization
    )

    flow_count = len(flows)

    return {
        "total_bytes": total_bytes,
        "flow_count": flow_count,
        "per_flow_avg": round(per_flow_avg, 6),
        "smoothed_utilization": round(smoothed_utilization, 6),
        "prefix_stats": {
            k: {
                "count": v["count"],
                "total_bytes": v["total_bytes"],
                "min_bytes": v["min_bytes"],
                "max_bytes": v["max_bytes"],
                "avg_bytes": round(v["avg_bytes"], 6),
            }
            for k, v in prefix_stats.items()
        },
        "inter_prefix_jitter": round(jitter, 6),
        "variance": round(variance, 6),
    }
