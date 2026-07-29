"""
Data Loader Module for SSA Pipeline
====================================
Loads and validates configuration from config.json.
Parses time series data and SSA parameters into numpy arrays.
"""

import json
import os
import numpy as np


# Required fields in config schema
REQUIRED_FIELDS = ["series", "window_length", "n_components", "grouping"]


def validate_config_schema(config):
    """
    Validates the configuration dictionary against the expected schema.
    
    Parameters
    ----------
    config : dict
        Raw configuration dictionary loaded from JSON.
        
    Returns
    -------
    list
        List of validation error messages. Empty if valid.
    """
    errors = []
    
    # Check required fields
    for field in REQUIRED_FIELDS:
        if field not in config:
            errors.append(f"Missing required field: '{field}'")
    
    if errors:
        return errors
    
    # Validate series
    if not isinstance(config["series"], list):
        errors.append("'series' must be a list of floats")
    elif len(config["series"]) < 2:
        errors.append("'series' must contain at least 2 elements")
    elif not all(isinstance(x, (int, float)) for x in config["series"]):
        errors.append("All elements in 'series' must be numeric")
    
    # Validate window_length
    if not isinstance(config["window_length"], int):
        errors.append("'window_length' must be an integer")
    elif config["window_length"] < 2:
        errors.append("'window_length' must be at least 2")
    elif config["window_length"] >= len(config["series"]):
        errors.append("'window_length' must be less than series length")
    
    # Validate n_components
    if not isinstance(config["n_components"], int):
        errors.append("'n_components' must be an integer")
    elif config["n_components"] < 1:
        errors.append("'n_components' must be at least 1")
    
    # Validate grouping
    if not isinstance(config["grouping"], list):
        errors.append("'grouping' must be a list of lists of integers")
    else:
        for i, group in enumerate(config["grouping"]):
            if not isinstance(group, list):
                errors.append(f"Group {i} must be a list of integers")
            elif not all(isinstance(idx, int) for idx in group):
                errors.append(f"All indices in group {i} must be integers")
    
    return errors


def load_config(config_path):
    """
    Load and validate SSA configuration from a JSON file.
    
    Parameters
    ----------
    config_path : str
        Path to the config.json file.
        
    Returns
    -------
    dict
        Parsed configuration with numpy arrays:
        - series: np.ndarray of float64
        - window_length: int
        - n_components: int  
        - grouping: list of lists of ints
        
    Raises
    ------
    FileNotFoundError
        If config file does not exist.
    ValueError
        If config fails schema validation.
    """
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    with open(config_path, 'r') as f:
        raw_config = json.load(f)
    
    # Validate schema
    validation_errors = validate_config_schema(raw_config)
    if validation_errors:
        error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {e}" for e in validation_errors)
        raise ValueError(error_msg)
    
    # Parse into structured format with numpy arrays
    parsed_config = {
        "series": np.array(raw_config["series"], dtype=np.float64),
        "window_length": raw_config["window_length"],
        "n_components": raw_config["n_components"],
        "grouping": raw_config["grouping"]
    }
    
    return parsed_config
