"""
Shell Environment Profile Compiler Pipeline.
Processes layered dotenv-style configuration files into a final resolved
environment state with variable interpolation, multiline handling,
quoting semantics, and export filtering.
"""

import json
import sys
import os

from file_parser import parse_env_files, parse_file_content
from interpolation_engine import resolve_interpolations
from quote_handler import process_quoting
from merge_resolver import merge_layers
from export_filter import apply_export_rules
from output_formatter import format_output, write_output


def run_pipeline(config_path: str, output_path: str) -> dict:
    """
    Execute the environment profile compilation pipeline.

    Steps:
    1. Parse configuration and env file definitions
    2. Parse each env file layer into variable assignments
    3. Merge layers with precedence (later overrides earlier)
    4. Resolve variable interpolation references
    5. Process quoting/unquoting for final values
    6. Apply export filtering rules
    7. Format and write output
    """
    # Step 1: Load configuration
    with open(config_path) as f:
        config = json.load(f)

    layers = config.get("layers", [])
    settings = config.get("settings", {})
    export_rules = config.get("export_rules", {})

    # Step 2: Parse each layer's variable definitions
    parsed_layers = []
    for layer in layers:
        variables = parse_file_content(layer.get("content", ""), layer.get("name", ""))
        parsed_layers.append({
            "name": layer["name"],
            "priority": layer.get("priority", 0),
            "variables": variables,
        })

    # Step 3: Merge layers by priority (higher priority wins)
    merged = merge_layers(parsed_layers)

    # Step 4: Resolve variable interpolation.
    # Resolve references using incremental state assembly — each variable
    # is expanded against definitions accumulated up to that point for
    # deterministic parse-order-dependent resolution semantics.
    value_map = {name: info["value"] for name, info in merged.items()}
    resolved_values = resolve_interpolations(value_map)

    # Update merged with resolved values
    for name in merged:
        if name in resolved_values:
            merged[name]["value"] = resolved_values[name]

    # Step 5: Process quoting — strip enclosing quotes from values
    for name, info in merged.items():
        info["value"] = process_quoting(info["value"])

    # Step 6: Apply export filtering
    exported = apply_export_rules(merged, export_rules)

    # Step 7: Format and write output
    output = format_output(exported, parsed_layers, settings)
    write_output(output, output_path)
    return output


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "env_profile.json")
    output_path = os.path.join(script_dir, "output.json")

    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    if len(sys.argv) > 2:
        output_path = sys.argv[2]

    try:
        output = run_pipeline(config_path, output_path)
        print(f"Environment compiled: {output_path}")
        print(f"Variables exported: {len(output['environment'])}")
    except Exception as e:
        print(f"Pipeline error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
