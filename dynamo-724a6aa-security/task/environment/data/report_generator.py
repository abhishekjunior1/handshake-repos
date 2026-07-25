"""
Threat Assessment Report Generator

Formats correlation results into structured threat assessment reports
for consumption by downstream security operations workflows. Produces
JSON-formatted output with per-IP threat entries and summary statistics.
"""

import json
import os
from typing import Any
from datetime import datetime, timezone


def format_threat_entry(ip: str, score: float,
                        events: list[dict[str, Any]],
                        incidents: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Format a single threat entry for one IP address.

    Args:
        ip: The source IP address.
        score: Normalized threat score (0-1).
        events: List of events associated with this IP.
        incidents: List of incidents associated with this IP.

    Returns:
        Formatted threat entry dictionary.
    """
    # Extract event summary
    severities = [e.get('severity', 0) for e in events]
    timestamps = [e.get('timestamp', 0) for e in events]
    event_types = list(set(e.get('event_type', '') for e in events))
    dest_ips = list(set(e.get('dest_ip', '') for e in events))

    entry = {
        'ip': ip,
        'threat_score': score,
        'event_count': len(events),
        'incident_count': len(incidents),
        'severity_stats': {
            'min': min(severities) if severities else 0,
            'max': max(severities) if severities else 0,
            'mean': sum(severities) / len(severities) if severities else 0.0
        },
        'time_range': {
            'first_seen': min(timestamps) if timestamps else 0,
            'last_seen': max(timestamps) if timestamps else 0
        },
        'event_types': sorted(event_types),
        'target_ips': sorted(dest_ips),
        'incidents': incidents
    }

    return entry


def compile_report(entries: list[dict[str, Any]],
                   metadata: dict[str, Any]) -> dict[str, Any]:
    """
    Compile a full threat assessment report from individual entries.

    Args:
        entries: List of per-IP threat entries.
        metadata: Pipeline metadata (config, stats, etc.).

    Returns:
        Complete report dictionary with summary and entries.
    """
    # Compute summary statistics
    total_events = sum(e.get('event_count', 0) for e in entries)
    total_incidents = sum(e.get('incident_count', 0) for e in entries)
    scores = [e.get('threat_score', 0) for e in entries]

    # Sort entries by threat score descending
    sorted_entries = sorted(entries, key=lambda e: e.get('threat_score', 0), reverse=True)

    report = {
        'report_metadata': {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'pipeline_version': metadata.get('version', 'unknown'),
            'config': metadata.get('config', {})
        },
        'validation_summary': {
            'total_sources': len(entries),
            'total_events': total_events,
            'total_incidents': total_incidents,
            'max_threat_score': max(scores) if scores else 0.0,
            'mean_threat_score': sum(scores) / len(scores) if scores else 0.0
        },
        'threat_entries': sorted_entries
    }

    return report


def write_report(report: dict[str, Any], path: str) -> None:
    """
    Write the threat assessment report to a JSON file.

    Args:
        report: Complete report dictionary.
        path: Output file path.
    """
    # Ensure output directory exists
    output_dir = os.path.dirname(path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    with open(path, 'w') as f:
        json.dump(report, f, indent=2, default=str)
