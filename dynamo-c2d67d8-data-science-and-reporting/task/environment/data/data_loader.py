"""
Data loader module for the biostatistics pipeline.

Handles reading study data from JSON format and validating the schema
to ensure all required fields are present before analysis begins.
"""

import json
import os


REQUIRED_TOP_LEVEL_KEYS = ["study_config", "groups", "analysis_params"]
REQUIRED_STUDY_CONFIG_KEYS = ["study_name", "comparisons"]
REQUIRED_COMPARISON_KEYS = ["group_a", "group_b"]
REQUIRED_GROUP_KEYS = ["measurements"]
REQUIRED_ANALYSIS_PARAMS_KEYS = ["alpha", "test_type"]


def load_study_data(filepath):
    """
    Load study data from a JSON file.

    Parameters
    ----------
    filepath : str
        Path to the JSON file containing study data.

    Returns
    -------
    dict
        Parsed study data dictionary.

    Raises
    ------
    FileNotFoundError
        If the input file does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Study data file not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    return data


def validate_schema(data):
    """
    Validate the structure of loaded study data against the expected schema.

    Checks for presence of required top-level keys, study configuration fields,
    comparison specifications, group data, and analysis parameters.

    Parameters
    ----------
    data : dict
        The parsed study data to validate.

    Returns
    -------
    dict
        Dictionary with 'valid' boolean and 'errors' list.
    """
    errors = []

    # Check top-level keys
    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            errors.append(f"Missing required top-level key: '{key}'")

    if errors:
        return {"valid": False, "errors": errors}

    # Validate study_config
    study_config = data["study_config"]
    for key in REQUIRED_STUDY_CONFIG_KEYS:
        if key not in study_config:
            errors.append(f"Missing required study_config key: '{key}'")

    # Validate comparisons
    if "comparisons" in study_config:
        comparisons = study_config["comparisons"]
        if not isinstance(comparisons, list) or len(comparisons) == 0:
            errors.append("'comparisons' must be a non-empty list")
        else:
            for i, comp in enumerate(comparisons):
                for key in REQUIRED_COMPARISON_KEYS:
                    if key not in comp:
                        errors.append(
                            f"Comparison {i}: missing required key '{key}'"
                        )

    # Validate groups
    groups = data["groups"]
    if not isinstance(groups, dict) or len(groups) == 0:
        errors.append("'groups' must be a non-empty dictionary")
    else:
        for group_name, group_data in groups.items():
            for key in REQUIRED_GROUP_KEYS:
                if key not in group_data:
                    errors.append(
                        f"Group '{group_name}': missing required key '{key}'"
                    )
            if "measurements" in group_data:
                measurements = group_data["measurements"]
                if not isinstance(measurements, list) or len(measurements) < 2:
                    errors.append(
                        f"Group '{group_name}': measurements must have at least 2 values"
                    )

    # Validate analysis_params
    analysis_params = data["analysis_params"]
    for key in REQUIRED_ANALYSIS_PARAMS_KEYS:
        if key not in analysis_params:
            errors.append(f"Missing required analysis_params key: '{key}'")

    # Cross-validate: all referenced groups exist
    if "comparisons" in study_config:
        available_groups = set(groups.keys())
        for comp in study_config["comparisons"]:
            for side in ["group_a", "group_b"]:
                if side in comp and comp[side] not in available_groups:
                    errors.append(
                        f"Comparison references non-existent group: '{comp[side]}'"
                    )

    return {"valid": len(errors) == 0, "errors": errors}


def extract_group_names(data):
    """
    Extract all group names from the study data.

    Parameters
    ----------
    data : dict
        Parsed study data.

    Returns
    -------
    list
        Sorted list of group names.
    """
    return sorted(data["groups"].keys())


def get_sample_sizes(data):
    """
    Get sample sizes for each group.

    Parameters
    ----------
    data : dict
        Parsed study data.

    Returns
    -------
    dict
        Dictionary mapping group names to their sample sizes.
    """
    sizes = {}
    for group_name, group_data in data["groups"].items():
        sizes[group_name] = len(group_data["measurements"])
    return sizes
