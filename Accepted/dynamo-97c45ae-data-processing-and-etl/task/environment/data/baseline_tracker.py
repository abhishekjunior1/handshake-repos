"""
Baseline tracker module.

Tracks cross-bin utilization baseline for the flow aggregation
pipeline. The baseline represents traffic load context carried
forward between bins to provide normalization for per-bin
utilization calculations.

Two tracking modes are supported:
- 'accumulate': Simple summation of bin totals
- 'smoothed': Exponential moving average with fixed alpha

The choice of mode depends on the pipeline's operational requirements:
- Accumulate mode is appropriate when downstream consumers need
  cumulative traffic accounting (billing, capacity planning).
- Smoothed mode is appropriate when the baseline should reflect
  recent traffic patterns for adaptive threshold computation
  (anomaly detection, burst management).
"""


def update_baseline(current_baseline, bin_total, mode):
    """
    Update the cross-bin utilization baseline.

    Parameters
    ----------
    current_baseline : float
        Current baseline value carried forward from previous bins.
    bin_total : float
        Total bytes from the current bin to incorporate.
    mode : str
        Update mode. One of:
        - 'accumulate': baseline = current + bin_total
          Maintains running total of all observed traffic.
        - 'smoothed': baseline = current * (1 - alpha) + bin_total * alpha
          Exponential moving average with alpha = 0.3.

    Returns
    -------
    float
        Updated baseline value.

    Raises
    ------
    ValueError
        If mode is not one of the supported values.

    Examples
    --------
    >>> update_baseline(1000.0, 500.0, 'accumulate')
    1500.0
    >>> update_baseline(1000.0, 500.0, 'smoothed')
    850.0
    """
    if mode == 'accumulate':
        # Simple accumulation: running total of all bin contributions
        return current_baseline + bin_total

    elif mode == 'smoothed':
        # Exponential moving average with fixed smoothing factor
        alpha = 0.3
        return current_baseline * (1 - alpha) + bin_total * alpha

    else:
        raise ValueError(f"Unknown baseline mode: {mode}. Use 'accumulate' or 'smoothed'.")
