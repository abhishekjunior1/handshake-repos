"""
Output formatting module for EVA pipeline.

Assembles pipeline results into the standardized JSON output schema
and handles file writing with proper serialization.
"""

import json
from typing import Dict, Any


def format_output(gev_params: Dict[str, float],
                  gpd_params: Dict[str, float],
                  return_levels: Dict[str, float],
                  exceedance_rate: float,
                  cluster_rate: float,
                  exceedance_count: int,
                  cluster_count: int,
                  extremal_index: float,
                  threshold: float,
                  qq_statistics: Dict[str, float],
                  goodness_of_fit: Dict[str, Any],
                  block_maxima_summary: Dict[str, Any],
                  diagnostic_flags: Dict[str, bool]) -> Dict[str, Any]:
    """
    Assemble all pipeline results into the output schema.

    Parameters
    ----------
    gev_params : dict
        GEV distribution parameters (location, scale, shape).
    gpd_params : dict
        GPD distribution parameters (scale, shape).
    return_levels : dict
        Return level estimates keyed by period string.
    exceedance_rate : float
        Proportion of observations exceeding threshold.
    cluster_rate : float
        Rate of independent clusters per observation.
    exceedance_count : int
        Total number of threshold exceedances.
    cluster_count : int
        Number of independent extreme event clusters.
    extremal_index : float
        Extremal index (theta = clusters / exceedances).
    threshold : float
        Exceedance threshold level.
    qq_statistics : dict
        QQ-plot diagnostic statistics.
    goodness_of_fit : dict
        GOF test results (p_value, pass).
    block_maxima_summary : dict
        Summary statistics of block maxima.
    diagnostic_flags : dict
        Model diagnostic flags.

    Returns
    -------
    dict
        Complete output conforming to the pipeline schema.
    """
    output = {
        "gev_params": {
            "location": gev_params["location"],
            "scale": gev_params["scale"],
            "shape": gev_params["shape"],
        },
        "gpd_params": {
            "scale": gpd_params["scale"],
            "shape": gpd_params["shape"],
        },
        "return_levels": return_levels,
        "exceedance_rate": round(exceedance_rate, 6),
        "cluster_rate": round(cluster_rate, 6),
        "exceedance_count": exceedance_count,
        "cluster_count": cluster_count,
        "extremal_index": round(extremal_index, 6),
        "threshold": threshold,
        "qq_statistics": qq_statistics,
        "goodness_of_fit": goodness_of_fit,
        "block_maxima_summary": block_maxima_summary,
        "diagnostic_flags": diagnostic_flags,
    }
    return output


def write_output(output: Dict[str, Any], filepath: str) -> None:
    """
    Write pipeline output to JSON file.

    Parameters
    ----------
    output : dict
        Formatted output dictionary.
    filepath : str
        Destination file path.
    """
    with open(filepath, "w") as f:
        json.dump(output, f, indent=2)
    print(f"Output written to: {filepath}")
