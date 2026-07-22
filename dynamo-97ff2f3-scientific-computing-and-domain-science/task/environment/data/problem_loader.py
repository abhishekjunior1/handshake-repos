"""
Problem loader module for the ODE solver pipeline.

Handles reading problem specifications from JSON format and validating
that all required fields are present and well-formed.
"""

import json
import os


REQUIRED_TOP_LEVEL_KEYS = ["system", "solver_config"]
REQUIRED_SYSTEM_KEYS = ["name", "equations", "initial_conditions", "t_start", "t_end"]
REQUIRED_SOLVER_KEYS = ["atol", "rtol"]


def load_problem(filepath):
    """
    Load an ODE problem specification from a JSON file.

    Parameters
    ----------
    filepath : str
        Path to the JSON problem specification.

    Returns
    -------
    dict
        Parsed problem specification.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Problem file not found: {filepath}")

    with open(filepath, "r") as f:
        data = json.load(f)

    return data


def validate_problem_spec(data):
    """
    Validate the structure of a problem specification.

    Parameters
    ----------
    data : dict
        Parsed problem data.

    Returns
    -------
    dict
        Dictionary with 'valid' boolean and 'errors' list.
    """
    errors = []

    for key in REQUIRED_TOP_LEVEL_KEYS:
        if key not in data:
            errors.append(f"Missing required key: '{key}'")

    if errors:
        return {"valid": False, "errors": errors}

    system = data["system"]
    for key in REQUIRED_SYSTEM_KEYS:
        if key not in system:
            errors.append(f"Missing system key: '{key}'")

    if "equations" in system:
        if not isinstance(system["equations"], list) or len(system["equations"]) == 0:
            errors.append("'equations' must be a non-empty list")

    if "initial_conditions" in system:
        if not isinstance(system["initial_conditions"], list):
            errors.append("'initial_conditions' must be a list")
        elif "equations" in system and len(system["initial_conditions"]) != len(system["equations"]):
            errors.append("Number of initial conditions must match number of equations")

    if "t_start" in system and "t_end" in system:
        if system["t_start"] >= system["t_end"]:
            errors.append("t_start must be less than t_end")

    solver_config = data["solver_config"]
    for key in REQUIRED_SOLVER_KEYS:
        if key not in solver_config:
            errors.append(f"Missing solver_config key: '{key}'")

    if "atol" in solver_config and solver_config["atol"] <= 0:
        errors.append("atol must be positive")
    if "rtol" in solver_config and solver_config["rtol"] <= 0:
        errors.append("rtol must be positive")

    return {"valid": len(errors) == 0, "errors": errors}


def get_problem_dimension(data):
    """Return the dimension (number of equations) of the ODE system."""
    return len(data["system"]["equations"])


def get_time_span(data):
    """Return (t_start, t_end) tuple."""
    return (data["system"]["t_start"], data["system"]["t_end"])
