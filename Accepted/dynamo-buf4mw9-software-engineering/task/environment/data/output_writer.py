"""PLC Historian Output Writer Module.

Formats migrated historian data into structured JSON output suitable
for ingestion by modern time-series databases (InfluxDB, TimescaleDB,
OSIsoft PI Web API).

Output Schema:
    {
        "metadata": {
            "source_format": "historian_v2",
            "migration_version": "1.0",
            "tag_count": <int>,
            "total_samples": <int>
        },
        "tags": [
            {
                "tag_id": <int>,
                "tag_type": <str>,
                "sample_count": <int>,
                "calibration_applied": <bool>,
                "samples": [
                    {
                        "timestamp_iso": <str>,
                        "value": <float>,
                        "quality_severity": <int>,
                        "interpolated": <bool>
                    },
                    ...
                ]
            },
            ...
        ]
    }
"""

import json
from typing import List, Dict, Any


def format_sample_output(sample: Dict[str, Any]) -> Dict[str, Any]:
    """Format a single sample for JSON output.

    Extracts the relevant fields and normalizes naming for the
    output schema.

    Args:
        sample: Internal sample dictionary with processing metadata.

    Returns:
        Cleaned output sample with standardized field names.
    """
    output = {
        'timestamp_iso': sample.get('timestamp_iso', ''),
        'value': sample.get('value', 0.0),
        'quality_severity': sample.get('severity', 0),
        'interpolated': sample.get('interpolated', False),
    }

    # Include compression metadata if present
    if 'compression_quality' in sample:
        output['compression_info'] = {
            'reconstructed': sample['compression_quality'].get('reconstructed', False),
            'max_error': sample['compression_quality'].get('max_error', 0.0),
        }

    return output


def format_tag_output(tag_id: int, tag_type: str,
                      samples: List[Dict[str, Any]],
                      calibration_applied: bool) -> Dict[str, Any]:
    """Format output for a single tag (process variable).

    Args:
        tag_id: Numeric tag identifier.
        tag_type: Tag type string ('analog' or 'discrete').
        samples: List of processed samples for this tag.
        calibration_applied: Whether calibration was applied.

    Returns:
        Tag output dictionary for JSON serialization.
    """
    formatted_samples = [format_sample_output(s) for s in samples]

    return {
        'tag_id': tag_id,
        'tag_type': tag_type,
        'sample_count': len(formatted_samples),
        'calibration_applied': calibration_applied,
        'samples': formatted_samples,
    }


def build_output(tags_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build the complete output structure with metadata.

    Args:
        tags_data: List of formatted tag output dictionaries.

    Returns:
        Complete output dictionary ready for JSON serialization.
    """
    total_samples = sum(t.get('sample_count', 0) for t in tags_data)

    return {
        'metadata': {
            'source_format': 'historian_v2',
            'migration_version': '1.0',
            'tag_count': len(tags_data),
            'total_samples': total_samples,
        },
        'tags': tags_data,
    }


def write_json_output(output: Dict[str, Any], path: str) -> None:
    """Write the output dictionary to a JSON file.

    Args:
        output: Complete output dictionary.
        path: File path for JSON output.
    """
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
        f.write('\n')
