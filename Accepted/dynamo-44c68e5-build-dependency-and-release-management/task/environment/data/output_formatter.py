"""JSON output formatting for pipeline results."""

import json


def format_output(store_paths: dict, build_plan: dict, system_info: dict) -> dict:
    """Assemble the final pipeline output dictionary."""
    return {
        'store_paths': store_paths,
        'build_plan': build_plan,
        'system': system_info,
    }


def write_output(output: dict, output_path: str) -> None:
    """Write formatted output to JSON file."""
    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2, sort_keys=True)


def format_summary(build_plan: dict) -> str:
    """Generate a human-readable build summary string."""
    return (f"Build plan: {build_plan['total_builds']} to build, "
            f"{build_plan['total_substitutes']} to substitute")
