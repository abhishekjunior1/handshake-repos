"""Event processing pipeline — reads events, produces windowed summaries."""
import json

from config import load_config, WINDOW_MINUTES
from parser import parse_timestamp, get_window, normalize_category
from aggregator import aggregate


def run(events_path="/app/events.json", output_path="/app/summary.json"):
    config = load_config()
    with open(events_path) as f:
        events = json.load(f)

    # Parse and normalize events
    parsed = []
    for ev in events:
        dt = parse_timestamp(ev["timestamp"])
        parsed.append({
            "event_id": ev.get("event_id", ""),
            "timestamp": ev["timestamp"],
            "category": normalize_category(ev["category"]),
            "window": get_window(dt, WINDOW_MINUTES),
            "priority": ev.get("priority", 1),
            "impact": ev.get("impact", 1.0),
            "severity": ev.get("severity", "low"),
        })

    # Sort events by timestamp before aggregation
    parsed.sort(key=lambda x: x["timestamp"])

    # Aggregate
    include_max = config.get("include_max_score", False)
    summary = aggregate(parsed, include_max)

    json.dump(summary, open(output_path, "w"), indent=2)
    print(f"Processed {sum(len(v) for v in summary.values())} windows")


if __name__ == "__main__":
    run()
