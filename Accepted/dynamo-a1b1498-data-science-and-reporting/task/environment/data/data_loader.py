"""
Data loader module for the survival analysis pipeline.

Handles reading patient cohort data from JSON format and validating
the schema to ensure all required fields are present before analysis.
"""

import json
import os


REQUIRED_TOP_LEVEL_KEYS = ["study_config", "patients", "analysis_params"]
REQUIRED_STUDY_CONFIG_KEYS = ["study_name", "group_field", "time_field", "event_field"]
REQUIRED_ANALYSIS_PARAMS_KEYS = ["alpha", "confidence_level"]


def load_cohort_data(filepath):
    """
    Load patient cohort data from a JSON file.

    Parameters
    ----------
    filepath : str
        Path to the JSON file containing cohort data.

    Returns
    -------
    dict
        Parsed cohort data dictionary.

    Raises
    ------
    FileNotFoundError
        If the input file does not exist.
    json.JSONDecodeError
        If the file contains invalid JSON.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Cohort data file not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    return data


def validate_cohort_schema(data):
    """
    Validate the structure of loaded cohort data against the expected schema.

    Checks for required keys, patient record structure, valid time and event
    values, and consistency of group labels.

    Parameters
    ----------
    data : dict
        The parsed cohort data to validate.

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

    if errors:
        return {"valid": False, "errors": errors}

    # Validate patients
    patients = data["patients"]
    if not isinstance(patients, list) or len(patients) < 2:
        errors.append("'patients' must be a list with at least 2 records")
    else:
        time_field = study_config["time_field"]
        event_field = study_config["event_field"]
        group_field = study_config["group_field"]

        for i, patient in enumerate(patients):
            if time_field not in patient:
                errors.append(f"Patient {i}: missing time field '{time_field}'")
            elif not isinstance(patient[time_field], (int, float)):
                errors.append(f"Patient {i}: time field must be numeric")
            elif patient[time_field] < 0:
                errors.append(f"Patient {i}: time field must be non-negative")

            if event_field not in patient:
                errors.append(f"Patient {i}: missing event field '{event_field}'")
            elif patient[event_field] not in (0, 1):
                errors.append(f"Patient {i}: event field must be 0 or 1")

            if group_field not in patient:
                errors.append(f"Patient {i}: missing group field '{group_field}'")

    # Validate analysis_params
    analysis_params = data["analysis_params"]
    for key in REQUIRED_ANALYSIS_PARAMS_KEYS:
        if key not in analysis_params:
            errors.append(f"Missing required analysis_params key: '{key}'")

    if "alpha" in analysis_params:
        alpha = analysis_params["alpha"]
        if not (0 < alpha < 1):
            errors.append("alpha must be between 0 and 1 (exclusive)")

    if "confidence_level" in analysis_params:
        cl = analysis_params["confidence_level"]
        if not (0 < cl < 1):
            errors.append("confidence_level must be between 0 and 1 (exclusive)")

    return {"valid": len(errors) == 0, "errors": errors}


def get_unique_groups(data):
    """
    Extract unique group labels from the patient data.

    Parameters
    ----------
    data : dict
        Parsed cohort data.

    Returns
    -------
    list
        Sorted list of unique group names.
    """
    group_field = data["study_config"]["group_field"]
    groups = set()
    for patient in data["patients"]:
        groups.add(patient[group_field])
    return sorted(groups)


def get_event_counts(data):
    """
    Count events and censored observations per group.

    Parameters
    ----------
    data : dict
        Parsed cohort data.

    Returns
    -------
    dict
        Dictionary mapping group names to event/censored counts.
    """
    group_field = data["study_config"]["group_field"]
    event_field = data["study_config"]["event_field"]

    counts = {}
    for patient in data["patients"]:
        g = patient[group_field]
        if g not in counts:
            counts[g] = {"events": 0, "censored": 0, "total": 0}
        counts[g]["total"] += 1
        if patient[event_field] == 1:
            counts[g]["events"] += 1
        else:
            counts[g]["censored"] += 1

    return counts
