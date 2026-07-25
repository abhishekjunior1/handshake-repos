"""CDC Event Stream Parser.

Parses raw CDC event records from JSON format into normalized internal
representation for downstream processing stages.
"""

import json
from datetime import datetime


class CDCEvent:
    """Represents a single CDC change event."""

    def __init__(self, event_id, table_name, operation, primary_key,
                 timestamp, payload, schema_version=1):
        self.event_id = event_id
        self.table_name = table_name
        self.operation = operation
        self.primary_key = primary_key
        self.timestamp = timestamp
        self.payload = payload
        self.schema_version = schema_version

    def to_dict(self):
        return {
            "event_id": self.event_id,
            "table_name": self.table_name,
            "operation": self.operation,
            "primary_key": self.primary_key,
            "timestamp": self.timestamp,
            "payload": self.payload,
            "schema_version": self.schema_version
        }


def parse_event_stream(filepath):
    """Load and parse CDC event stream from JSON file.

    Validates event structure, normalizes timestamps, and returns
    a list of CDCEvent objects ordered by their original position.
    """
    with open(filepath, "r") as f:
        raw_data = json.load(f)

    events = []
    for idx, record in enumerate(raw_data.get("events", [])):
        event = _parse_single_event(record, idx)
        if event is not None:
            events.append(event)

    return events


def _parse_single_event(record, position):
    """Parse and validate a single event record."""
    required_fields = ["event_id", "table_name", "operation",
                       "primary_key", "timestamp", "payload"]

    for field in required_fields:
        if field not in record:
            return None

    operation = record["operation"].upper()
    if operation not in ("INSERT", "UPDATE", "DELETE"):
        return None

    timestamp = _normalize_timestamp(record["timestamp"])
    if timestamp is None:
        return None

    payload = record.get("payload", {})
    schema_version = record.get("schema_version", 1)

    return CDCEvent(
        event_id=record["event_id"],
        table_name=record["table_name"],
        operation=operation,
        primary_key=record["primary_key"],
        timestamp=timestamp,
        payload=payload,
        schema_version=schema_version
    )


def _normalize_timestamp(ts_value):
    """Normalize timestamp to ISO format string.

    Accepts ISO format strings or epoch milliseconds.
    Returns normalized ISO string or None if unparseable.
    """
    if isinstance(ts_value, (int, float)):
        dt = datetime.utcfromtimestamp(ts_value / 1000.0)
        return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"

    if isinstance(ts_value, str):
        try:
            if ts_value.endswith("Z"):
                ts_value = ts_value[:-1] + "+00:00"
            dt = datetime.fromisoformat(ts_value)
            return dt.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        except (ValueError, TypeError):
            return None

    return None


def extract_table_names(events):
    """Extract unique table names from event stream preserving first-seen order."""
    seen = set()
    tables = []
    for event in events:
        if event.table_name not in seen:
            seen.add(event.table_name)
            tables.append(event.table_name)
    return tables


def group_events_by_table(events):
    """Group events by their source table name."""
    groups = {}
    for event in events:
        if event.table_name not in groups:
            groups[event.table_name] = []
        groups[event.table_name].append(event)
    return groups


def get_schema_versions(events):
    """Extract all distinct schema versions from events."""
    versions = set()
    for event in events:
        versions.add(event.schema_version)
    return sorted(versions)
