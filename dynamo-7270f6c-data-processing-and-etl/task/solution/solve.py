import os
import re

DATA_DIR = "/app/data"
if not os.path.isdir(DATA_DIR):
    DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "environment", "data")


def fix_pipeline():
    path = os.path.join(DATA_DIR, "pipeline.py")
    with open(path, "r") as f:
        content = f.read()

    # Fix: move aggregation AFTER deduplication
    content = content.replace(
        "    aggregation = aggregate_records(transformed)\n\n    merged = deduplicate_records(transformed)",
        "    merged = deduplicate_records(transformed)\n\n    aggregation = aggregate_records(merged)",
    )

    with open(path, "w") as f:
        f.write(content)
    print("Fixed pipeline.py: aggregation now runs after deduplication")


def fix_merger():
    path = os.path.join(DATA_DIR, "merger.py")
    with open(path, "r") as f:
        content = f.read()

    # Fix: only overwrite non-null fields (upsert semantics)
    content = content.replace(
        "    merged = dict(existing)\n    for key, value in winner.items():\n        merged[key] = value\n    return merged",
        "    merged = dict(existing)\n    for key, value in winner.items():\n        if value is not None:\n            merged[key] = value\n    return merged",
    )

    with open(path, "w") as f:
        f.write(content)
    print("Fixed merger.py: merge_record_pair now uses upsert semantics")


def fix_aggregator():
    path = os.path.join(DATA_DIR, "aggregator.py")
    with open(path, "r") as f:
        content = f.read()

    # Fix: use effective_date for SCD type-2 records
    content = content.replace(
        "def assign_window(record):\n    ts = parse_timestamp(record.get(\"timestamp\"))\n    if ts is None:\n        return None\n    return get_window_key(ts)",
        "def assign_window(record):\n    if record.get(\"scd_type\") == 2:\n        ts = parse_timestamp(record.get(\"effective_date\"))\n    else:\n        ts = parse_timestamp(record.get(\"timestamp\"))\n    if ts is None:\n        return None\n    return get_window_key(ts)",
    )

    with open(path, "w") as f:
        f.write(content)
    print("Fixed aggregator.py: assign_window now uses effective_date for SCD type-2")


if __name__ == "__main__":
    fix_pipeline()
    fix_merger()
    fix_aggregator()
    print("All fixes applied successfully.")
