"""
Event deduplication module. Removes duplicate events within a batch
based on a specified identifier field.
"""


def deduplicate_window(events, dedup_field="event_id"):
    """
    Remove duplicate events from a single window's event batch.

    Parameters
    ----------
    events : list of dict
        Events in a single window.
    dedup_field : str
        Field to use for identity comparison.

    Returns
    -------
    list of dict
        Events with within-window duplicates removed.
    """
    seen = set()
    result = []
    for event in events:
        eid = event.get(dedup_field)
        if eid is None:
            result.append(event)
            continue
        if eid not in seen:
            seen.add(eid)
            result.append(event)
    return result
