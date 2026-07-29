"""
Bin assignment module. Assigns flow records to tumbling time bins
aligned to the epoch based on their timestamp field.

Tumbling windows are non-overlapping, fixed-size intervals.
Each flow is assigned to exactly one bin.
"""


def assign_to_bins(flows, bin_duration):
    """
    Assign flow records to tumbling time bins based on timestamp.

    Each bin covers the interval [bin_start, bin_start + bin_duration).
    Bin keys are the start timestamp of each bin (integer seconds).

    Parameters
    ----------
    flows : list of dict
        Flow records with 'timestamp' field (seconds since epoch).
    bin_duration : int or float
        Bin duration in seconds. Must be positive.

    Returns
    -------
    dict
        Mapping of bin_start (int) -> list of flow records in that bin.

    Examples
    --------
    >>> flows = [{"timestamp": 5}, {"timestamp": 35}, {"timestamp": 65}]
    >>> bins = assign_to_bins(flows, 30)
    >>> sorted(bins.keys())
    [0, 30, 60]
    """
    if bin_duration <= 0:
        raise ValueError("bin_duration must be positive")

    bins = {}
    for flow in flows:
        ts = flow["timestamp"]
        # Compute the bin start aligned to epoch
        bin_start = int(ts // bin_duration) * bin_duration
        if bin_start not in bins:
            bins[bin_start] = []
        bins[bin_start].append(flow)

    return bins
