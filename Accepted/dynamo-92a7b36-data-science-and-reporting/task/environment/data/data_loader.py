"""Data loading and validation module for meta-analysis pipeline.

Handles reading study-level effect sizes and standard errors from JSON,
validates required fields, and structures data for downstream analysis.
"""

import json
import sys
from typing import Any


def load_meta_data(filepath: str) -> dict[str, Any]:
    """Load meta-analysis data from a JSON file.

    Args:
        filepath: Path to the JSON file containing study data.

    Returns:
        Dictionary with validated study data including effects, standard errors,
        study labels, and optional subgroup assignments.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If required fields are missing or data is malformed.
    """
    try:
        with open(filepath, "r") as f:
            raw_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Data file not found at {filepath}", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in {filepath}: {e}", file=sys.stderr)
        raise ValueError(f"Invalid JSON: {e}")

    validate_structure(raw_data)
    return parse_studies(raw_data)


def validate_structure(raw_data: dict[str, Any]) -> None:
    """Validate the top-level structure of the input data.

    Args:
        raw_data: Raw dictionary loaded from JSON.

    Raises:
        ValueError: If required top-level keys are missing.
    """
    required_keys = ["studies", "analysis_name", "effect_measure"]
    missing = [k for k in required_keys if k not in raw_data]
    if missing:
        raise ValueError(f"Missing required keys: {missing}")

    if not isinstance(raw_data["studies"], list):
        raise ValueError("'studies' must be a list")

    if len(raw_data["studies"]) < 2:
        raise ValueError("At least 2 studies required for meta-analysis")


def parse_studies(raw_data: dict[str, Any]) -> dict[str, Any]:
    """Parse and validate individual study entries.

    Args:
        raw_data: Validated raw dictionary from JSON.

    Returns:
        Structured dictionary with numpy-compatible lists of effects,
        standard errors, labels, and metadata.

    Raises:
        ValueError: If any study is missing required fields or has invalid values.
    """
    effects = []
    std_errors = []
    labels = []
    subgroups = []

    for i, study in enumerate(raw_data["studies"]):
        if "effect_size" not in study:
            raise ValueError(f"Study {i}: missing 'effect_size'")
        if "std_error" not in study:
            raise ValueError(f"Study {i}: missing 'std_error'")
        if "label" not in study:
            raise ValueError(f"Study {i}: missing 'label'")

        es = float(study["effect_size"])
        se = float(study["std_error"])

        if se <= 0:
            raise ValueError(f"Study {i}: std_error must be positive, got {se}")

        effects.append(es)
        std_errors.append(se)
        labels.append(study["label"])
        subgroups.append(study.get("subgroup", "default"))

    return {
        "effects": effects,
        "std_errors": std_errors,
        "labels": labels,
        "subgroups": subgroups,
        "analysis_name": raw_data["analysis_name"],
        "effect_measure": raw_data["effect_measure"],
        "num_studies": len(effects),
        "unique_subgroups": sorted(set(subgroups)),
    }
