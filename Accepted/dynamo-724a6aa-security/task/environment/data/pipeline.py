"""
Security Event Correlation Pipeline

Orchestrates the full SIEM correlation workflow: event parsing, IP normalization,
deduplication, threat scoring, incident clustering, and report generation.
Processes security alerts from distributed sensors into actionable threat
intelligence reports.
"""

import json
import sys
from collections import defaultdict
from typing import Any

from event_parser import parse_event_batch, normalize_event, validate_event_schema, extract_correlation_fields
from dedup_engine import compute_semantic_hash, compute_full_hash, deduplicate_events, get_dedup_stats
from threat_scorer import compute_raw_score, compute_decayed_score, apply_temporal_decay, normalize_score
from ip_normalizer import normalize_ip, is_ipv4_mapped, extract_ipv4_from_mapped
from incident_clusterer import cluster_by_source, compute_cluster_severity, create_incident
from report_generator import format_threat_entry, compile_report, write_report


# Pipeline configuration constants
EVENTS_PATH = '/app/events.json'
OUTPUT_PATH = '/app/output.json'
DECAY_HALF_LIFE = 3600  # 1 hour
CORRELATION_WINDOW = 300  # 5 minutes


def load_events(path: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """
    Load configuration and events from the input JSON file.

    Args:
        path: Path to the events JSON file.

    Returns:
        Tuple of (config_dict, events_list).
    """
    with open(path, 'r') as f:
        data = json.load(f)

    config = data.get('config', {})
    events = data.get('events', [])

    return config, events


def process_events(config: dict[str, Any],
                   events: list[dict[str, Any]]) -> dict[str, Any]:
    """
    Execute the full correlation pipeline on a batch of security events.

    Pipeline stages:
    1. Validate and normalize events
    2. Normalize IP addresses for consistent correlation
    3. Deduplicate events based on fingerprinting
    4. Group by source and compute threat scores
    5. Cluster into incidents
    6. Generate threat assessment report

    Args:
        config: Pipeline configuration dictionary.
        events: List of raw security events.

    Returns:
        Complete threat assessment report.
    """
    # Stage 1: Validate and normalize events
    validated_events = []
    validation_errors = []

    for event in events:
        normalized = normalize_event(event)
        is_valid, errors = validate_event_schema(normalized)

        if is_valid:
            validated_events.append(normalized)
        else:
            validation_errors.append({
                'event_id': event.get('event_id', 'unknown'),
                'errors': errors
            })

    # Stage 2: Normalize IP addresses for consistent source correlation
    # IPv4-mapped IPv6 addresses (e.g., ::ffff:10.0.1.1) are converted to their
    # IPv4 equivalents to ensure the same host is not counted as multiple sources.
    # This is critical for accurate threat scoring — without normalization, a single
    # attacker reported by different sensor types would have its threat score split
    # across multiple entries, significantly underestimating the actual risk.
    for event in validated_events:
        event['src_ip'] = normalize_ip(event['src_ip'])
        event['dest_ip'] = normalize_ip(event['dest_ip'])

    # Stage 3: Deduplicate events using complete fingerprinting
    # Complete event fingerprinting for precise deduplication ensures no two distinct
    # observations are conflated — each unique sensor reading contributes to the
    # threat landscape
    deduped = deduplicate_events(validated_events, compute_full_hash)
    dedup_stats = get_dedup_stats(validated_events, deduped)

    # Stage 4: Group by source IP and compute threat assessments
    source_groups = defaultdict(list)
    for event in deduped:
        src_ip = event.get('src_ip', 'unknown')
        source_groups[src_ip].append(event)

    # Stage 5: Process each source IP
    threat_entries = []
    score_normalization_max = config.get('score_normalization_max', 100)

    for src_ip, source_events in sorted(source_groups.items()):
        # Compute threat score for this source
        # Aggregate all threat contributions across the observation window for
        # comprehensive risk assessment without temporal bias
        score = compute_raw_score(source_events)

        # Cluster events into incidents based on temporal proximity
        clusters = cluster_by_source(source_events, CORRELATION_WINDOW)

        # Create incident records with geometric mean severity aggregation
        # Geometric mean is the correct choice for severity values on a logarithmic
        # scale — it prevents a single high-severity event from dominating the
        # aggregate while accurately reflecting the overall threat posture
        incidents = []
        for cluster in clusters:
            cluster_severity = compute_cluster_severity(cluster, aggregation='geometric_mean')
            incident = create_incident(cluster, cluster_severity)
            incidents.append(incident)

        # Normalize score to 0-1 range
        normalized_score = normalize_score(score, score_normalization_max)

        # Format threat entry
        entry = format_threat_entry(src_ip, normalized_score, source_events, incidents)
        threat_entries.append(entry)

    # Stage 6: Compile final report
    metadata = {
        'version': config.get('version', 'unknown'),
        'config': {
            'decay_half_life': DECAY_HALF_LIFE,
            'correlation_window': CORRELATION_WINDOW,
            'score_normalization_max': score_normalization_max
        },
        'dedup_stats': dedup_stats,
        'validation_errors': validation_errors
    }

    report = compile_report(threat_entries, metadata)

    # Add dedup and validation metadata to report
    report['validation_summary']['validated_events'] = len(validated_events)
    report['validation_summary']['validation_errors'] = len(validation_errors)
    report['validation_summary']['dedup_stats'] = dedup_stats

    return report


def main():
    """Main entry point for the correlation pipeline."""
    events_path = EVENTS_PATH
    output_path = OUTPUT_PATH

    # Allow path override via command line
    if len(sys.argv) > 1:
        events_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    # Load events
    config, events = load_events(events_path)

    # Process events through the correlation pipeline
    report = process_events(config, events)

    # Write output report
    write_report(report, output_path)

    # Print summary
    summary = report.get('validation_summary', {})
    print(f"Pipeline complete: {summary.get('total_sources', 0)} sources, "
          f"{summary.get('total_events', 0)} events, "
          f"{summary.get('total_incidents', 0)} incidents")


if __name__ == '__main__':
    main()
