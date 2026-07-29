"""
Security Event Parser Module

Parses and validates security events from JSON input. Each event contains
fields for identification, network addressing, rule matching, and severity
classification from distributed sensor infrastructure.
"""

import json
import copy
from typing import Any


# Required fields for a valid security event
REQUIRED_FIELDS = [
    'event_id',
    'timestamp',
    'src_ip',
    'dest_ip',
    'rule_id',
    'severity',
    'payload_signature',
    'sensor_id',
    'event_type'
]

# Valid severity range
SEVERITY_MIN = 1
SEVERITY_MAX = 10

# Valid event types
VALID_EVENT_TYPES = [
    'intrusion_attempt',
    'malware_detected',
    'port_scan',
    'brute_force',
    'data_exfiltration',
    'privilege_escalation',
    'lateral_movement',
    'command_control',
    'denial_of_service',
    'policy_violation'
]

# Fields used for correlation analysis
CORRELATION_FIELDS = ['src_ip', 'dest_ip', 'rule_id', 'payload_signature', 'event_type']


def parse_event_batch(raw_json: str) -> list[dict[str, Any]]:
    """
    Parse a batch of security events from raw JSON string.

    Args:
        raw_json: JSON string containing a list of event dictionaries.

    Returns:
        List of parsed event dictionaries.

    Raises:
        ValueError: If JSON is malformed or not a list.
    """
    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as e:
        raise ValueError(f"Malformed JSON input: {e}")

    if not isinstance(data, list):
        raise ValueError("Event batch must be a JSON array")

    parsed_events = []
    for i, raw_event in enumerate(data):
        if not isinstance(raw_event, dict):
            raise ValueError(f"Event at index {i} is not a dictionary")
        normalized = normalize_event(raw_event)
        parsed_events.append(normalized)

    return parsed_events


def normalize_event(event: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a single security event by ensuring consistent types and formats.

    Args:
        event: Raw event dictionary.

    Returns:
        Normalized event dictionary with consistent field types.
    """
    normalized = copy.deepcopy(event)

    # Ensure timestamp is numeric
    if 'timestamp' in normalized:
        normalized['timestamp'] = float(normalized['timestamp'])

    # Ensure severity is integer within valid range
    if 'severity' in normalized:
        severity = int(normalized['severity'])
        severity = max(SEVERITY_MIN, min(SEVERITY_MAX, severity))
        normalized['severity'] = severity

    # Ensure string fields are stripped
    string_fields = ['event_id', 'src_ip', 'dest_ip', 'rule_id',
                     'payload_signature', 'sensor_id', 'event_type']
    for field in string_fields:
        if field in normalized and isinstance(normalized[field], str):
            normalized[field] = normalized[field].strip()

    return normalized


def validate_event_schema(event: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate that an event conforms to the expected schema.

    Args:
        event: Event dictionary to validate.

    Returns:
        Tuple of (is_valid, list_of_errors).
    """
    errors = []

    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in event:
            errors.append(f"Missing required field: {field}")

    # Validate field types if present
    if 'timestamp' in event:
        try:
            ts = float(event['timestamp'])
            if ts <= 0:
                errors.append("Timestamp must be positive")
        except (TypeError, ValueError):
            errors.append("Timestamp must be numeric")

    if 'severity' in event:
        try:
            sev = int(event['severity'])
            if sev < SEVERITY_MIN or sev > SEVERITY_MAX:
                errors.append(f"Severity must be between {SEVERITY_MIN} and {SEVERITY_MAX}")
        except (TypeError, ValueError):
            errors.append("Severity must be an integer")

    if 'event_type' in event:
        if event['event_type'] not in VALID_EVENT_TYPES:
            errors.append(f"Invalid event_type: {event['event_type']}")

    if 'src_ip' in event:
        if not isinstance(event['src_ip'], str) or len(event['src_ip']) == 0:
            errors.append("src_ip must be a non-empty string")

    if 'dest_ip' in event:
        if not isinstance(event['dest_ip'], str) or len(event['dest_ip']) == 0:
            errors.append("dest_ip must be a non-empty string")

    return (len(errors) == 0, errors)


def extract_correlation_fields(event: dict[str, Any]) -> dict[str, Any]:
    """
    Extract the subset of fields used for event correlation.

    These fields determine whether two events are semantically related
    and should be considered part of the same attack pattern.

    Args:
        event: Full event dictionary.

    Returns:
        Dictionary containing only correlation-relevant fields.
    """
    correlation_data = {}
    for field in CORRELATION_FIELDS:
        if field in event:
            correlation_data[field] = event[field]
        else:
            correlation_data[field] = None

    # Include severity as it affects threat scoring
    if 'severity' in event:
        correlation_data['severity'] = event['severity']

    # Include timestamp for temporal correlation
    if 'timestamp' in event:
        correlation_data['timestamp'] = event['timestamp']

    return correlation_data
