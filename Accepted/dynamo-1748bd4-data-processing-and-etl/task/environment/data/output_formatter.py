"""
Output Formatter Module
========================

Formats the final pipeline output into a structured JSON representation
suitable for consumption by downstream systems, APIs, and visualization
tools.

The output includes:
- Pipeline metadata (execution timestamp, parameters, input summary)
- Per-level aggregated results with normalized values
- Diagnostic and quality metrics
- Source data lineage information
"""

import json
from datetime import datetime
from typing import List, Dict, Any, Optional


# Output format version for schema evolution tracking
OUTPUT_FORMAT_VERSION = "2.1.0"

# Maximum decimal places for floating point values in output
MAX_DECIMAL_PLACES = 6


def round_floats(obj: Any, decimal_places: int = MAX_DECIMAL_PLACES) -> Any:
    """
    Recursively round all float values in a nested structure.

    Parameters
    ----------
    obj : Any
        Object to process. Can be dict, list, float, or other types.
    decimal_places : int, optional
        Number of decimal places to round to.

    Returns
    -------
    Any
        Object with all floats rounded.
    """
    if isinstance(obj, float):
        return round(obj, decimal_places)
    elif isinstance(obj, dict):
        return {k: round_floats(v, decimal_places) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [round_floats(item, decimal_places) for item in obj]
    return obj


def format_pipeline_output(normalized_data: Dict[str, List[Dict[str, Any]]],
                           pipeline_metadata: Dict[str, Any],
                           diagnostics: Dict[str, Any],
                           input_summary: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the complete pipeline output as a structured dictionary.

    Combines normalized results with metadata, diagnostics, and lineage
    information into a single output structure ready for JSON serialization.

    Parameters
    ----------
    normalized_data : Dict[str, List[Dict[str, Any]]]
        Normalized hierarchical data from the normalizer module.
    pipeline_metadata : Dict[str, Any]
        Metadata about the pipeline execution (params, timing, etc.).
    diagnostics : Dict[str, Any]
        Quality and validation diagnostics.
    input_summary : Dict[str, Any]
        Summary of the input data characteristics.

    Returns
    -------
    Dict[str, Any]
        Complete formatted output structure.
    """
    output = {
        "format_version": OUTPUT_FORMAT_VERSION,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "pipeline": pipeline_metadata,
        "input_summary": input_summary,
        "results": {},
        "diagnostics": diagnostics
    }

    # Structure results by hierarchy level
    for level_name, level_data in normalized_data.items():
        output["results"][level_name] = {
            "record_count": len(level_data),
            "records": round_floats(level_data)
        }

    return output


def write_json_output(output: Dict[str, Any], output_path: str,
                      indent: int = 2) -> None:
    """
    Write the formatted output to a JSON file.

    Parameters
    ----------
    output : Dict[str, Any]
        The formatted pipeline output.
    output_path : str
        File path to write the JSON output.
    indent : int, optional
        JSON indentation level. Default is 2.
    """
    rounded_output = round_floats(output)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(rounded_output, f, indent=indent, ensure_ascii=False,
                  default=str)


def generate_summary_line(output: Dict[str, Any]) -> str:
    """
    Generate a one-line summary of the pipeline output for logging.

    Parameters
    ----------
    output : Dict[str, Any]
        The formatted pipeline output.

    Returns
    -------
    str
        A concise summary string.
    """
    levels = list(output.get("results", {}).keys())
    total_records = sum(
        level_data.get("record_count", 0)
        for level_data in output.get("results", {}).values()
    )

    return (
        f"Pipeline output: {len(levels)} levels, "
        f"{total_records} total records, "
        f"format v{output.get('format_version', 'unknown')}"
    )
