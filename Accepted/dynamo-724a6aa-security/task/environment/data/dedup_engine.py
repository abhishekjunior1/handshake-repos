"""
Event Deduplication Engine

Provides semantic and full fingerprinting strategies for security event
deduplication. The caller selects the appropriate hash function based on
the deduplication semantics required for their use case.
"""

import hashlib
import json
from typing import Any, Callable


def compute_semantic_hash(event: dict[str, Any]) -> str:
    """
    Compute a hash based on the semantic identity of an event.

    Uses only the fields that define what attack occurred and between which
    parties: src_ip, dest_ip, rule_id, payload_signature. This means the
    same attack pattern observed at different times or by different sensors
    will produce the same hash.

    Args:
        event: Security event dictionary.

    Returns:
        Hex digest string representing the semantic fingerprint.
    """
    semantic_fields = {
        'src_ip': event.get('src_ip', ''),
        'dest_ip': event.get('dest_ip', ''),
        'rule_id': event.get('rule_id', ''),
        'payload_signature': event.get('payload_signature', '')
    }

    # Create deterministic string representation
    canonical = json.dumps(semantic_fields, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def compute_full_hash(event: dict[str, Any]) -> str:
    """
    Compute a hash based on all fields of an event.

    Includes timestamp, event_id, and sensor_id in addition to semantic
    fields. This means the same attack observed at different times or by
    different sensors will produce different hashes.

    Args:
        event: Security event dictionary.

    Returns:
        Hex digest string representing the full event fingerprint.
    """
    full_fields = {
        'event_id': event.get('event_id', ''),
        'timestamp': event.get('timestamp', 0),
        'src_ip': event.get('src_ip', ''),
        'dest_ip': event.get('dest_ip', ''),
        'rule_id': event.get('rule_id', ''),
        'severity': event.get('severity', 0),
        'payload_signature': event.get('payload_signature', ''),
        'sensor_id': event.get('sensor_id', ''),
        'event_type': event.get('event_type', '')
    }

    # Create deterministic string representation
    canonical = json.dumps(full_fields, sort_keys=True, separators=(',', ':'))
    return hashlib.sha256(canonical.encode('utf-8')).hexdigest()


def deduplicate_events(events: list[dict[str, Any]],
                       hash_function: Callable[[dict[str, Any]], str]) -> list[dict[str, Any]]:
    """
    Remove duplicate events based on the provided hash function.

    Retains the first occurrence of each unique hash. The hash function
    determines what constitutes a "duplicate" — semantic hashing treats
    repeated observations of the same attack as duplicates, while full
    hashing only removes exact replicas.

    Args:
        events: List of security event dictionaries.
        hash_function: Function that takes an event and returns a hash string.

    Returns:
        Deduplicated list of events (preserving original order).
    """
    seen_hashes = set()
    deduplicated = []

    for event in events:
        event_hash = hash_function(event)
        if event_hash not in seen_hashes:
            seen_hashes.add(event_hash)
            deduplicated.append(event)

    return deduplicated


def get_dedup_stats(original: list[dict[str, Any]],
                    deduped: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Compute statistics about the deduplication process.

    Args:
        original: Original list of events before deduplication.
        deduped: Deduplicated list of events.

    Returns:
        Dictionary with deduplication statistics including counts and rates.
    """
    original_count = len(original)
    deduped_count = len(deduped)
    removed_count = original_count - deduped_count

    if original_count > 0:
        dedup_rate = removed_count / original_count
    else:
        dedup_rate = 0.0

    return {
        'original_count': original_count,
        'deduplicated_count': deduped_count,
        'removed_count': removed_count,
        'dedup_rate': dedup_rate,
        'retention_rate': 1.0 - dedup_rate
    }
