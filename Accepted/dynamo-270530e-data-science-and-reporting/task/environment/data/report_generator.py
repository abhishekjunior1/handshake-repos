"""
Report Generator Module for SSA Pipeline
==========================================
Formats the SSA pipeline output into a structured JSON report
with all results rounded to consistent precision.
"""

import json
import numpy as np


# Precision for floating point values in output
FLOAT_PRECISION = 10


def _round_value(value):
    """
    Rounds a single float value to the specified precision.
    
    Parameters
    ----------
    value : float
        Value to round.
        
    Returns
    -------
    float
        Rounded value.
    """
    if isinstance(value, (int, np.integer)):
        return int(value)
    elif isinstance(value, (float, np.floating)):
        return round(float(value), FLOAT_PRECISION)
    return value


def _round_list(lst):
    """
    Recursively rounds all float values in a list structure.
    
    Parameters
    ----------
    lst : list
        List (potentially nested) of numeric values.
        
    Returns
    -------
    list
        List with all floats rounded to FLOAT_PRECISION decimal places.
    """
    result = []
    for item in lst:
        if isinstance(item, list):
            result.append(_round_list(item))
        elif isinstance(item, (float, np.floating)):
            result.append(round(float(item), FLOAT_PRECISION))
        elif isinstance(item, (int, np.integer)):
            result.append(int(item))
        else:
            result.append(item)
    return result


def _round_dict(d):
    """
    Recursively rounds all float values in a dictionary.
    
    Parameters
    ----------
    d : dict
        Dictionary with numeric values.
        
    Returns
    -------
    dict
        Dictionary with all floats rounded.
    """
    result = {}
    for key, value in d.items():
        if isinstance(value, dict):
            result[key] = _round_dict(value)
        elif isinstance(value, list):
            result[key] = _round_list(value)
        elif isinstance(value, (float, np.floating)):
            result[key] = round(float(value), FLOAT_PRECISION)
        elif isinstance(value, (int, np.integer)):
            result[key] = int(value)
        else:
            result[key] = value
    return result


def generate_report(output):
    """
    Generates a formatted report dictionary from pipeline output.
    
    All floating point values are rounded to 10 decimal places for
    consistent output format.
    
    Parameters
    ----------
    output : dict
        Raw pipeline output containing:
        - reconstructed_components: list of lists
        - contribution_ratios: list of floats
        - eigenvalue_spectrum: list of floats
        - w_correlation_matrix: list of lists
        - residual_series: list of floats
        - diagnostics: dict with quality metrics
        
    Returns
    -------
    dict
        Formatted report with all values rounded.
    """
    report = {
        "reconstructed_components": _round_list(output["reconstructed_components"]),
        "contribution_ratios": _round_list(output["contribution_ratios"]),
        "eigenvalue_spectrum": _round_list(output["eigenvalue_spectrum"]),
        "w_correlation_matrix": _round_list(output["w_correlation_matrix"]),
        "residual_series": _round_list(output["residual_series"]),
        "diagnostics": _round_dict(output["diagnostics"])
    }
    
    return report


def save_report(report, output_path):
    """
    Saves the report dictionary to a JSON file.
    
    Parameters
    ----------
    report : dict
        Formatted report dictionary.
    output_path : str
        Path to the output JSON file.
    """
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2)


def load_report(report_path):
    """
    Loads a previously generated report from JSON.
    
    Parameters
    ----------
    report_path : str
        Path to the report JSON file.
        
    Returns
    -------
    dict
        Loaded report dictionary.
    """
    with open(report_path, 'r') as f:
        return json.load(f)
