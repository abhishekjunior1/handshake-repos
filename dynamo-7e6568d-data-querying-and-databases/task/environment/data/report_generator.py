"""Report generator - formats analysis results as structured JSON output."""

import json


def generate_report(results, output_path):
    """Write analysis results to JSON file.

    Args:
        results: Dictionary containing all analysis results
        output_path: Path for output JSON file

    Returns:
        dict: The results written
    """
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    return results
