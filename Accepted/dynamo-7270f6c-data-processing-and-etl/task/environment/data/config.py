import os
import json
from datetime import datetime, timedelta


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOURCE_PATH = os.path.join(BASE_DIR, "source.json")
OUTPUT_PATH = os.path.join(BASE_DIR, "output.json")

WINDOW_SIZE_DAYS = 7
LATE_ARRIVAL_THRESHOLD_DAYS = 3

REQUIRED_FIELDS = ["id", "timestamp", "amount", "category", "region"]
OPTIONAL_FIELDS = ["effective_date", "scd_type", "status", "priority", "description"]

CATEGORY_MULTIPLIERS = {
    "electronics": 1.15,
    "clothing": 1.08,
    "food": 1.03,
    "services": 1.20,
    "utilities": 1.05,
    "healthcare": 1.12,
    "transportation": 1.10,
}

REGION_TAX_RATES = {
    "north": 0.06,
    "south": 0.07,
    "east": 0.055,
    "west": 0.08,
    "central": 0.065,
}

PRIORITY_WEIGHTS = {
    "critical": 4,
    "high": 3,
    "medium": 2,
    "low": 1,
}

STATUS_TRANSITIONS = {
    "pending": ["active", "cancelled"],
    "active": ["completed", "cancelled"],
    "completed": [],
    "cancelled": [],
}

VALID_STATUSES = list(STATUS_TRANSITIONS.keys())
EPOCH = datetime(2020, 1, 1)


def load_json(path):
    with open(path, "r") as f:
        return json.load(f)


def save_json(data, path):
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def parse_timestamp(ts_str):
    if ts_str is None:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(ts_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def get_window_key(dt):
    days_since_epoch = (dt - EPOCH).days
    window_num = days_since_epoch // WINDOW_SIZE_DAYS
    window_start = EPOCH + timedelta(days=window_num * WINDOW_SIZE_DAYS)
    return window_start.strftime("%Y-%m-%d")


def is_late_arrival(record_ts, effective_ts):
    if record_ts is None or effective_ts is None:
        return False
    return abs((record_ts - effective_ts).days) > LATE_ARRIVAL_THRESHOLD_DAYS
