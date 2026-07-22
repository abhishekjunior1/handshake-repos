"""Report Generator module for the anomaly detection pipeline.

Produces structured JSON output containing the full anomaly detection
report including per-segment analysis results, anomaly classifications,
and pipeline metadata.
"""

import json
from typing import List, Dict, Any, Optional


class ReportError(Exception):
    """Raised when report generation encounters an error."""
    pass


def generate_report(segments_info: List[Dict[str, Any]],
                    anomaly_results: List[Dict[str, Any]],
                    pipeline_config: Dict[str, Any],
                    spectral_summary: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the structured anomaly detection report.

    Combines segment analysis, anomaly classifications, and pipeline
    configuration into a single JSON-serializable output structure.

    Args:
        segments_info: Per-segment metadata and statistics.
        anomaly_results: Global anomaly classification results.
        pipeline_config: Configuration parameters used.
        spectral_summary: Summary spectral statistics.

    Returns:
        Complete report dictionary.
    """
    # Count anomalies
    n_anomalies = sum(1 for r in anomaly_results if r.get('is_anomaly', False))
    n_total = len(anomaly_results)

    # Compute severity statistics
    severities = [r['severity'] for r in anomaly_results if r.get('is_anomaly', False)]
    mean_severity = sum(severities) / len(severities) if severities else 0.0
    max_severity = max(severities) if severities else 0.0

    report = {
        'summary': {
            'total_observations': n_total,
            'n_anomalies': n_anomalies,
            'anomaly_rate': n_anomalies / n_total if n_total > 0 else 0.0,
            'n_segments': len(segments_info),
            'mean_severity': round(mean_severity, 6),
            'max_severity': round(max_severity, 6)
        },
        'segments': _format_segments(segments_info),
        'anomalies': _format_anomalies(anomaly_results),
        'spectral': spectral_summary,
        'config': pipeline_config
    }

    return report


def _format_segments(segments_info: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format segment information for the report.

    Args:
        segments_info: Raw segment metadata.

    Returns:
        Formatted segment entries.
    """
    formatted = []
    for i, seg in enumerate(segments_info):
        entry = {
            'segment_id': i,
            'start': seg.get('start', 0),
            'end': seg.get('end', 0),
            'length': seg.get('length', 0),
            'mean': round(seg.get('mean', 0.0), 6),
            'variance': round(seg.get('variance', 0.0), 6),
            'n_anomalies': seg.get('n_anomalies', 0),
            'threshold': round(seg.get('threshold', 0.0), 6)
        }
        formatted.append(entry)

    return formatted


def _format_anomalies(anomaly_results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Format anomaly results for the report.

    Only includes observations flagged as anomalous.

    Args:
        anomaly_results: Full classification results.

    Returns:
        Formatted anomaly entries (anomalies only).
    """
    anomalies = []
    for result in anomaly_results:
        if result.get('is_anomaly', False):
            entry = {
                'global_index': result.get('global_index', result.get('index', 0)),
                'segment': result.get('segment', 0),
                'score': round(result['score'], 6),
                'threshold': round(result['threshold'], 6),
                'severity': round(result['severity'], 6)
            }
            anomalies.append(entry)

    return anomalies


def write_report(report: Dict[str, Any], output_path: str) -> None:
    """Write the report to a JSON file.

    Args:
        report: Report dictionary to serialize.
        output_path: Absolute path for the output file.
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            f.write('\n')
    except OSError as e:
        raise ReportError(f"Failed to write report: {e}")


def validate_report(report: Dict[str, Any]) -> bool:
    """Validate report structure for completeness.

    Checks that all required top-level keys exist and have
    the correct types.

    Args:
        report: Report dictionary to validate.

    Returns:
        True if report is valid.
    """
    required_keys = ['summary', 'segments', 'anomalies', 'spectral', 'config']
    for key in required_keys:
        if key not in report:
            return False

    summary = report['summary']
    required_summary = ['total_observations', 'n_anomalies', 'anomaly_rate',
                        'n_segments', 'mean_severity', 'max_severity']
    for key in required_summary:
        if key not in summary:
            return False

    return True
