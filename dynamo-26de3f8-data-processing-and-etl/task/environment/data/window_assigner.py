"""
Window assignment module. Assigns events to tumbling time windows
aligned to the epoch.
"""


def assign_to_windows(events, window_size):
    """
    Assign events to tumbling windows based on timestamp.

    Parameters
    ----------
    events : list of dict
        Events with 'timestamp' field.
    window_size : float
        Window size in seconds.

    Returns
    -------
    dict
        Mapping of window_start -> list of events.
    """
    windows = {}
    for event in events:
        ts = event["timestamp"]
        window_start = int(ts // window_size) * window_size
        if window_start not in windows:
            windows[window_start] = []
        windows[window_start].append(event)
    return windows
