"""
Sampler deduplication module.

In a multi-collector NetFlow/sFlow deployment, the same flow may be
observed by multiple collectors (e.g., ingress and egress sampling
points, redundant collectors for HA). This module deduplicates
flow observations within a bin based on their flow_id.

Only the first observation of each flow_id is kept; subsequent
duplicates from other collectors are discarded.
"""


def deduplicate_bin(flows, dedup_field="flow_id"):
    """
    Remove duplicate flow observations from a single bin.

    Multiple collectors may report the same logical flow. This
    function keeps only the first observation of each unique flow_id,
    preserving the original ordering of first appearances.

    Parameters
    ----------
    flows : list of dict
        Flow records in a single time bin, potentially containing
        duplicates from multiple collectors.
    dedup_field : str
        Field to use for identity comparison. Default is 'flow_id'.

    Returns
    -------
    list of dict
        Deduplicated flow records with duplicates removed.

    Examples
    --------
    >>> flows = [
    ...     {"flow_id": "f1", "collector": "col-1", "bytes": 100},
    ...     {"flow_id": "f1", "collector": "col-2", "bytes": 100},
    ...     {"flow_id": "f2", "collector": "col-1", "bytes": 200},
    ... ]
    >>> deduped = deduplicate_bin(flows)
    >>> len(deduped)
    2
    >>> deduped[0]["flow_id"]
    'f1'
    """
    seen = set()
    result = []

    for flow in flows:
        fid = flow.get(dedup_field)
        if fid is None:
            # Flows without an ID are always kept
            result.append(flow)
            continue
        if fid not in seen:
            seen.add(fid)
            result.append(flow)

    return result
