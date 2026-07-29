"""
Report builder module.

Formats the final output report for the flow aggregation pipeline,
combining per-bin traffic results with stream-level summary statistics.
"""


def build_report(stream_name, bin_duration, smoothing_alpha, bin_results,
                 total_flows, total_after_dedup):
    """
    Build the structured output report.

    Parameters
    ----------
    stream_name : str
        Name of the flow stream being processed.
    bin_duration : int
        Bin duration in seconds.
    smoothing_alpha : float
        Smoothing factor used for EMA computations.
    bin_results : list of dict
        Per-bin traffic computation results.
    total_flows : int
        Total number of raw flow records in the input.
    total_after_dedup : int
        Total flows remaining after deduplication across all bins.

    Returns
    -------
    dict
        Structured report with config, per-bin results, and summary.
    """
    return {
        "stream_name": stream_name,
        "config": {
            "bin_duration_sec": bin_duration,
            "smoothing_alpha": smoothing_alpha,
        },
        "bins": bin_results,
        "summary": {
            "total_flows": total_flows,
            "flows_after_dedup": total_after_dedup,
            "duplicates_removed": total_flows - total_after_dedup,
            "bins_produced": len(bin_results),
        },
    }
