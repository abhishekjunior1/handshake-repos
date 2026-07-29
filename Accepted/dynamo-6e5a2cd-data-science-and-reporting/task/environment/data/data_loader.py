"""
Data loading and validation module for EVA pipeline.

Handles JSON input parsing, schema validation, and extraction of
configuration parameters required for extreme value analysis.
"""

import json
import sys
from typing import Dict, Any, List, Tuple


def load_input_data(filepath: str) -> Dict[str, Any]:
    """
    Load and validate input JSON data file.

    Parameters
    ----------
    filepath : str
        Path to the JSON input file containing observations and parameters.

    Returns
    -------
    dict
        Validated configuration dictionary with all required fields.

    Raises
    ------
    FileNotFoundError
        If the specified file does not exist.
    ValueError
        If required fields are missing or have invalid values.
    """
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: Input file '{filepath}' not found.", file=sys.stderr)
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{filepath}': {e}", file=sys.stderr)
        raise ValueError(f"Malformed JSON input: {e}")

    # Validate required fields
    required_fields = ["observations", "threshold", "run_length",
                       "return_periods", "block_size", "confidence_level"]
    missing = [f for f in required_fields if f not in data]
    if missing:
        raise ValueError(f"Missing required fields: {missing}")

    # Validate observations
    observations = data["observations"]
    if not isinstance(observations, list) or len(observations) < 10:
        raise ValueError("Observations must be a list with at least 10 values.")

    if not all(isinstance(v, (int, float)) for v in observations):
        raise ValueError("All observations must be numeric values.")

    # Validate threshold
    threshold = float(data["threshold"])
    if threshold <= 0:
        raise ValueError("Threshold must be positive.")

    # Validate run_length
    run_length = int(data["run_length"])
    if run_length < 1:
        raise ValueError("Run length must be at least 1.")

    # Validate return periods
    return_periods = data["return_periods"]
    if not isinstance(return_periods, list) or not all(p > 0 for p in return_periods):
        raise ValueError("Return periods must be a list of positive numbers.")

    # Validate block_size
    block_size = int(data["block_size"])
    if block_size < 2:
        raise ValueError("Block size must be at least 2.")

    # Validate confidence level
    confidence_level = float(data["confidence_level"])
    if not (0.0 < confidence_level < 1.0):
        raise ValueError("Confidence level must be between 0 and 1.")

    return {
        "observations": [float(x) for x in observations],
        "threshold": threshold,
        "run_length": run_length,
        "return_periods": sorted([int(p) for p in return_periods]),
        "block_size": block_size,
        "confidence_level": confidence_level,
    }


def extract_exceedances(observations: List[float],
                        threshold: float) -> Tuple[List[float], List[int]]:
    """
    Extract threshold exceedances from observation series.

    Returns exceedance values (observation - threshold) and their indices
    in the original series for use in temporal declustering.

    Parameters
    ----------
    observations : list of float
        Complete observation time series.
    threshold : float
        Exceedance threshold level.

    Returns
    -------
    tuple of (list of float, list of int)
        Exceedance magnitudes (obs - threshold) and their indices.
    """
    exceedances = []
    indices = []
    for i, obs in enumerate(observations):
        if obs > threshold:
            exceedances.append(obs - threshold)
            indices.append(i)
    return exceedances, indices
