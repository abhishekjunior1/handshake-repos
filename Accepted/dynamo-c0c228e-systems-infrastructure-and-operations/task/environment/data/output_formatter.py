"""
Output formatter for the Shell Environment Profile Compiler.
Formats the final compiled environment into a structured JSON output.
"""

import json


def format_output(exported: dict, parsed_layers: list, settings: dict) -> dict:
    """Format the final output structure."""
    # Build environment map (sorted by variable name)
    env_map = {}
    for var_name, var_info in sorted(exported.items()):
        env_map[var_name] = var_info["value"]

    # Build source attribution
    source_map = {}
    for var_name, var_info in sorted(exported.items()):
        source_map[var_name] = var_info.get("source", "unknown")

    # Build layer summary
    layer_summary = []
    for layer in parsed_layers:
        layer_summary.append({
            "name": layer["name"],
            "priority": layer["priority"],
            "variable_count": len(layer["variables"]),
        })

    output = {
        "version": "1.0",
        "format": "compiled-env-profile",
        "environment": env_map,
        "metadata": {
            "source_attribution": source_map,
            "layers": layer_summary,
            "total_variables": len(env_map),
            "settings": settings,
        },
    }

    return output


def write_output(output: dict, output_path: str) -> None:
    """Write formatted output to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)
