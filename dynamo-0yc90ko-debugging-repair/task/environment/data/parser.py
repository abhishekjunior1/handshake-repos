"""Event parsing and normalization."""
from datetime import datetime, timedelta


def parse_timestamp(ts_str):
    """Parse ISO timestamp to datetime."""
    ts_str = ts_str.replace('Z', '+00:00')
    return datetime.fromisoformat(ts_str)


def get_window(dt, window_minutes):
    """Assign datetime to a time-window bucket."""
    minutes_since_midnight = dt.hour * 60 + dt.minute
    window_index = minutes_since_midnight // window_minutes
    window_start = dt.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(
        minutes=window_index * window_minutes)
    return window_start.strftime("%Y-%m-%dT%H:%M")


def normalize_category(category):
    """Normalize category string for grouping.

    Categories are case-insensitive and strip trailing whitespace.
    """
    return category.strip().lower()
