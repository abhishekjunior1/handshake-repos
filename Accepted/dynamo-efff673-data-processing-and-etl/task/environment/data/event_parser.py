"""
Event stream parser and validator.

Handles parsing of raw event records from the input stream configuration,
validates event schema integrity, and extracts typed fields for downstream
processing stages.
"""

from typing import Any


REQUIRED_FIELDS = {"event_id", "timestamp", "partition_key", "value", "event_type"}
VALID_EVENT_TYPES = {"measurement", "control", "heartbeat"}


def parse_event_stream(raw_events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse and validate raw event records from stream configuration.

    Each event must contain: event_id, timestamp, partition_key, value, event_type.
    Invalid events are filtered out with a parsing error record.
    """
    parsed_events = []
    parse_errors = []

    for idx, raw_event in enumerate(raw_events):
        validation_result = _validate_event_schema(raw_event, idx)
        if validation_result is not None:
            parse_errors.append(validation_result)
            continue

        parsed_event = _extract_typed_fields(raw_event)
        parsed_events.append(parsed_event)

    return parsed_events


def _validate_event_schema(event: dict[str, Any], index: int) -> dict[str, Any] | None:
    """Validate that an event record contains all required fields with valid types."""
    missing_fields = REQUIRED_FIELDS - set(event.keys())
    if missing_fields:
        return {
            "index": index,
            "error": f"missing fields: {sorted(missing_fields)}",
            "event_id": event.get("event_id", f"unknown_{index}")
        }

    if not isinstance(event["timestamp"], (int, float)):
        return {
            "index": index,
            "error": "timestamp must be numeric",
            "event_id": event["event_id"]
        }

    if not isinstance(event["value"], (int, float)):
        return {
            "index": index,
            "error": "value must be numeric",
            "event_id": event["event_id"]
        }

    if event["event_type"] not in VALID_EVENT_TYPES:
        return {
            "index": index,
            "error": f"invalid event_type: {event['event_type']}",
            "event_id": event["event_id"]
        }

    return None


def _extract_typed_fields(raw_event: dict[str, Any]) -> dict[str, Any]:
    """Extract and normalize typed fields from a validated event record."""
    return {
        "event_id": str(raw_event["event_id"]),
        "timestamp": float(raw_event["timestamp"]),
        "partition_key": str(raw_event["partition_key"]),
        "value": float(raw_event["value"]),
        "event_type": str(raw_event["event_type"]),
        "metadata": raw_event.get("metadata", {})
    }


def get_partition_keys(events: list[dict[str, Any]]) -> list[str]:
    """Extract unique partition keys from parsed events in encounter order."""
    seen = set()
    keys = []
    for event in events:
        pk = event["partition_key"]
        if pk not in seen:
            seen.add(pk)
            keys.append(pk)
    return keys


def filter_by_type(events: list[dict[str, Any]], event_type: str) -> list[dict[str, Any]]:
    """Filter events to only those matching the specified type."""
    return [e for e in events if e["event_type"] == event_type]
