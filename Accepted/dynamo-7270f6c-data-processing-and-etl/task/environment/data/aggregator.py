from config import parse_timestamp, get_window_key, is_late_arrival


def assign_window(record):
    ts = parse_timestamp(record.get("timestamp"))
    if ts is None:
        return None
    return get_window_key(ts)


def create_empty_window(window_key):
    return {
        "window_start": window_key,
        "record_count": 0,
        "total_amount": 0.0,
        "total_adjusted_amount": 0.0,
        "avg_priority_score": 0.0,
        "categories": {},
        "regions": {},
        "priority_sum": 0.0,
        "late_arrivals": 0,
    }


def accumulate_record(window, record):
    window["record_count"] += 1
    window["total_amount"] += record.get("amount", 0)
    window["total_adjusted_amount"] += record.get("adjusted_amount", 0)
    window["priority_sum"] += record.get("priority_score", 0)

    category = record.get("category", "unknown")
    window["categories"][category] = window["categories"].get(category, 0) + 1

    region = record.get("region", "unknown")
    window["regions"][region] = window["regions"].get(region, 0) + 1

    if record.get("is_late"):
        window["late_arrivals"] += 1


def finalize_windows(windows):
    for window_key in windows:
        window = windows[window_key]
        count = window["record_count"]
        if count > 0:
            window["avg_priority_score"] = round(
                window["priority_sum"] / count, 4
            )
        window["total_amount"] = round(window["total_amount"], 2)
        window["total_adjusted_amount"] = round(window["total_adjusted_amount"], 2)
        del window["priority_sum"]
    return windows


def compute_late_reassignments(records, windows):
    count = 0
    for record in records:
        if not record.get("is_late"):
            continue
        ts = parse_timestamp(record.get("timestamp"))
        eff = parse_timestamp(record.get("effective_date"))
        if ts is None or eff is None:
            continue
        ts_window = get_window_key(ts)
        eff_window = get_window_key(eff)
        if ts_window != eff_window and eff_window in windows:
            count += 1
    return count


def aggregate_records(records):
    windows = {}

    for record in records:
        window_key = assign_window(record)
        if window_key is None:
            continue
        if window_key not in windows:
            windows[window_key] = create_empty_window(window_key)
        accumulate_record(windows[window_key], record)

    finalize_windows(windows)
    late_reassignments = compute_late_reassignments(records, windows)

    return {
        "windows": windows,
        "total_records_processed": len(records),
        "total_windows": len(windows),
        "late_arrival_reassignments": late_reassignments,
    }
