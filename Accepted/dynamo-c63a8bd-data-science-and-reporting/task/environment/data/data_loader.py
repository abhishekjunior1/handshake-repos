"""
Data loading and validation for harmonic decomposition pipeline.

Handles JSON input parsing, schema validation, and series preprocessing.
Computes basic series statistics needed by downstream modules.
"""

import json
import math


def load_forecast_config(path):
    """Load decomposition configuration from JSON file.

    Args:
        path: Path to JSON configuration file.

    Returns:
        Validated configuration dictionary with series and parameters.

    Raises:
        ValueError: If configuration fails validation.
    """
    with open(path, 'r') as f:
        config = json.load(f)

    validate_config(config)
    config = compute_series_stats(config)
    return config


def validate_config(config):
    """Validate the decomposition configuration schema.

    Required fields:
        - series: list of numeric values (length >= 5)
        - max_harmonics: maximum number of harmonics to extract
        - window_type: spectral window type

    Args:
        config: Dictionary loaded from JSON.

    Raises:
        ValueError: If required fields are missing or invalid.
    """
    if 'series' not in config:
        raise ValueError("Configuration must contain 'series' field")

    series = config['series']
    if not isinstance(series, list) or len(series) < 5:
        raise ValueError("Series must have at least 5 observations")

    for i, val in enumerate(series):
        if not isinstance(val, (int, float)):
            raise ValueError(f"Series[{i}] is not numeric: {val}")
        if math.isnan(val) or math.isinf(val):
            raise ValueError(f"Series[{i}] is not finite: {val}")

    if 'max_harmonics' not in config:
        config['max_harmonics'] = 5

    valid_windows = ('rectangular', 'hann', 'hamming')
    wt = config.get('window_type', 'rectangular')
    if wt not in valid_windows:
        raise ValueError(f"window_type must be one of {valid_windows}, got '{wt}'")


def compute_series_stats(config):
    """Compute global series statistics for downstream use.

    Adds:
        - series_mean: arithmetic mean
        - series_variance: population variance
        - n: series length

    Args:
        config: Validated configuration dictionary.

    Returns:
        Configuration with added statistics.
    """
    series = config['series']
    n = len(series)
    series_mean = sum(series) / n
    series_variance = sum((x - series_mean) ** 2 for x in series) / n

    config['series_mean'] = series_mean
    config['series_variance'] = series_variance
    config['n'] = n

    return config
