"""Configuration loader for CIS compliance scanner.

Loads and validates system configuration files, benchmark definitions,
and waiver/exception policies from JSON input.
"""

import json
import sys
from typing import Any


def load_configuration(config_path: str) -> dict[str, Any]:
    """Load and validate the primary configuration file.

    Expected top-level keys:
      - benchmark: defines the rule hierarchy (profiles, sections, controls)
      - system_config: the system state being evaluated
      - waivers: optional exception/waiver definitions
      - settings: evaluation parameters

    Returns validated configuration dictionary.
    """
    try:
        with open(config_path, "r") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    _validate_structure(config)
    return config


def _validate_structure(config: dict[str, Any]) -> None:
    """Validate that all required top-level sections exist."""
    required_sections = ["benchmark", "system_config", "settings"]
    for section in required_sections:
        if section not in config:
            print(f"Missing required section: {section}", file=sys.stderr)
            sys.exit(1)

    _validate_benchmark(config["benchmark"])
    _validate_system_config(config["system_config"])
    _validate_settings(config["settings"])


def _validate_benchmark(benchmark: dict[str, Any]) -> None:
    """Validate benchmark structure has profiles with sections and controls."""
    if "profiles" not in benchmark:
        print("Benchmark must contain 'profiles' key", file=sys.stderr)
        sys.exit(1)

    for profile in benchmark["profiles"]:
        if "id" not in profile or "sections" not in profile:
            print("Each profile must have 'id' and 'sections'", file=sys.stderr)
            sys.exit(1)

        for section in profile["sections"]:
            if "id" not in section or "controls" not in section:
                print("Each section must have 'id' and 'controls'", file=sys.stderr)
                sys.exit(1)

            for control in section["controls"]:
                _validate_control(control)


def _validate_control(control: dict[str, Any]) -> None:
    """Validate individual control definition."""
    required_fields = ["id", "title", "type", "severity"]
    for field in required_fields:
        if field not in control:
            print(f"Control missing required field: {field}", file=sys.stderr)
            sys.exit(1)

    valid_types = ["scored", "informational"]
    if control["type"] not in valid_types:
        print(f"Invalid control type: {control['type']}", file=sys.stderr)
        sys.exit(1)

    if "cvss_score" not in control:
        control["cvss_score"] = _default_cvss_for_severity(control["severity"])


def _default_cvss_for_severity(severity: str) -> float:
    """Map severity level to default CVSS base score."""
    severity_map = {
        "critical": 9.5,
        "high": 7.5,
        "medium": 5.0,
        "low": 2.5,
        "informational": 0.0,
    }
    return severity_map.get(severity.lower(), 5.0)


def _validate_system_config(system_config: dict[str, Any]) -> None:
    """Validate system configuration has required resource definitions."""
    if "resources" not in system_config:
        print("system_config must contain 'resources' key", file=sys.stderr)
        sys.exit(1)

    for resource in system_config["resources"]:
        if "id" not in resource or "type" not in resource:
            print("Each resource must have 'id' and 'type'", file=sys.stderr)
            sys.exit(1)
        if "properties" not in resource:
            resource["properties"] = {}


def _validate_settings(settings: dict[str, Any]) -> None:
    """Validate evaluation settings."""
    if "evaluation_profile" not in settings:
        print("Settings must specify 'evaluation_profile'", file=sys.stderr)
        sys.exit(1)

    defaults = {
        "fail_threshold": 0.7,
        "include_informational_in_score": False,
        "risk_weighted_scoring": True,
        "inheritance_mode": "full_chain",
        "exception_match_mode": "glob",
    }

    for key, default_value in defaults.items():
        if key not in settings:
            settings[key] = default_value


def extract_resources(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract resource list from validated configuration."""
    return config["system_config"]["resources"]


def extract_benchmark(config: dict[str, Any]) -> dict[str, Any]:
    """Extract benchmark definition from validated configuration."""
    return config["benchmark"]


def extract_waivers(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract waiver/exception list from configuration.

    Returns empty list if no waivers defined.
    """
    return config.get("waivers", [])


def extract_settings(config: dict[str, Any]) -> dict[str, Any]:
    """Extract evaluation settings from configuration."""
    return config["settings"]
