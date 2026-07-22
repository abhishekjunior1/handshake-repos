"""Event aggregation into time-windowed summaries."""
from config import compute_score


def aggregate(events_parsed, include_max):
    """Aggregate parsed events into category/window buckets.

    Each bucket tracks: count, total_score, max_score.
    Duplicate events within a window are counted only once.
    """
    buckets = {}
    seen = {}

    for ev in events_parsed:
        key = f"{ev['category']}|{ev['window']}"
        if key not in buckets:
            buckets[key] = {"count": 0, "total_score": 0, "max_score": 0}
            seen[key] = set()

        dedup_key = ev["timestamp"]
        if dedup_key in seen[key]:
            continue
        seen[key].add(dedup_key)

        score = compute_score(ev["priority"], ev["impact"], ev["severity"])
        buckets[key]["count"] += 1
        buckets[key]["total_score"] += score
        buckets[key]["max_score"] = max(buckets[key]["max_score"], score)

    # Build output
    summary = {}
    for key, data in sorted(buckets.items()):
        category, window = key.split("|")
        if category not in summary:
            summary[category] = []
        entry = {
            "window": window,
            "count": data["count"],
            "total_score": data["total_score"],
        }
        if include_max:
            entry["max_score"] = data["max_score"]
        summary[category].append(entry)

    return summary
