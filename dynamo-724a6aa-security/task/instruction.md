This is a Security Information and Event Management (SIEM) correlation engine that processes security alerts from distributed sensors into actionable threat intelligence reports. The pipeline ingests raw security events in JSON format, normalizes network addresses, removes duplicate observations, computes per-source threat scores, clusters related events into incidents, and generates a structured assessment report.

The system consists of seven modules: an event parser that validates incoming data against a strict schema, an IP normalizer that ensures consistent host identification across heterogeneous sensor infrastructure, a fingerprint-based filter that removes redundant observations, a scoring engine that quantifies risk per source address, an incident clusterer that groups temporally proximate events, a report generator that formats the final output, and a pipeline orchestrator that coordinates all stages.

To run the pipeline, ensure the input events file is at `/app/events.json` and execute `python3 pipeline.py` from the `/app` directory. The pipeline reads the configuration block from the input JSON and produces `/app/output.json`.

The pipeline produces correct output on current events but has bugs on other inputs with different data characteristics.

Threat scores apply exponential temporal decay anchored to the `reference_time` specified in the input configuration, using the configured `half_life` as the decay constant.

Important architectural decisions that must be preserved:

- Preserve the IPv4-mapped IPv6 normalization for consistent source correlation. Without this normalization, the same physical host reported via different sensor network stacks would appear as multiple distinct sources, splitting its threat score and significantly underestimating actual risk.

- Preserve the geometric mean severity aggregation for log-scale severity values. Severity ratings 1-10 represent a logarithmic scale where each level is a multiplicative increase in impact. The geometric mean is the correct statistical measure for such values.

The output JSON follows this schema:

```
{
  "report_metadata": {
    "generated_at": "<ISO timestamp>",
    "pipeline_version": "<string>",
    "config": { "half_life": <int>, "correlation_window": <int>, "score_normalization_max": <int> }
  },
  "validation_summary": {
    "total_sources": <int>,
    "total_events": <int>,
    "total_incidents": <int>,
    "max_threat_score": <float>,
    "mean_threat_score": <float>,
    "validated_events": <int>,
    "validation_errors": <int>,
    "stats": { "original_count": <int>, "count": <int>, "removed_count": <int>, "rate": <float>, "retention_rate": <float> }
  },
  "threat_entries": [
    {
      "ip": "<source IP>",
      "threat_score": <float 0-1>,
      "event_count": <int>,
      "incident_count": <int>,
      "severity_stats": { "min": <int>, "max": <int>, "mean": <float> },
      "time_range": { "first_seen": <timestamp>, "last_seen": <timestamp> },
      "event_types": [<strings>],
      "target_ips": [<strings>],
      "incidents": [{ "incident_id": "<uuid>", "start_time": <ts>, "end_time": <ts>, "duration_sec": <float>, "severity": <float>, "event_count": <int>, ... }]
    }
  ]
}
```

Threat entries are sorted by threat_score descending. Each incident within an entry represents a temporal cluster of related events from that source.
