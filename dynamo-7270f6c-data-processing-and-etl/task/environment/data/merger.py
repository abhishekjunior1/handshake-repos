from config import parse_timestamp


def resolve_timestamp_conflict(existing, incoming):
    existing_ts = parse_timestamp(existing.get("timestamp"))
    incoming_ts = parse_timestamp(incoming.get("timestamp"))

    if existing_ts is None and incoming_ts is None:
        return incoming
    if existing_ts is None:
        return incoming
    if incoming_ts is None:
        return existing
    if incoming_ts >= existing_ts:
        return incoming
    return existing


def merge_record_pair(existing, incoming):
    winner = resolve_timestamp_conflict(existing, incoming)
    merged = dict(existing)
    for key, value in winner.items():
        merged[key] = value
    return merged


def compute_change_log(previous_state, current_state):
    prev_map = {r["id"]: r for r in previous_state}
    changes = []

    for record in current_state:
        record_id = record["id"]
        if record_id not in prev_map:
            changes.append({
                "id": record_id,
                "type": "insert",
                "fields_changed": list(record.keys()),
            })
        else:
            old = prev_map[record_id]
            changed_fields = []
            for key in set(list(record.keys()) + list(old.keys())):
                if record.get(key) != old.get(key):
                    changed_fields.append(key)
            if changed_fields:
                changes.append({
                    "id": record_id,
                    "type": "update",
                    "fields_changed": changed_fields,
                })

    for record_id in prev_map:
        if not any(r["id"] == record_id for r in current_state):
            changes.append({
                "id": record_id,
                "type": "delete",
                "fields_changed": [],
            })

    return changes


def deduplicate_records(records):
    seen = {}
    insertion_order = []

    for record in records:
        record_id = record.get("id")
        if record_id is None:
            continue

        if record_id in seen:
            existing = seen[record_id]
            merged = merge_record_pair(existing, record)
            seen[record_id] = merged
        else:
            seen[record_id] = dict(record)
            insertion_order.append(record_id)

    return [seen[rid] for rid in insertion_order]


def compute_merge_statistics(original_count, merged_count):
    duplicates_removed = original_count - merged_count
    dedup_ratio = duplicates_removed / original_count if original_count > 0 else 0.0
    return {
        "original_count": original_count,
        "merged_count": merged_count,
        "duplicates_removed": duplicates_removed,
        "dedup_ratio": round(dedup_ratio, 4),
    }
