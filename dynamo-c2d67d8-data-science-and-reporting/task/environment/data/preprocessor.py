"""
Preprocessor module for the biostatistics pipeline.

Handles data cleaning operations including outlier detection via
the IQR method, winsorization of extreme values, and optional
normalization/centering of measurement data.
"""

import math


def detect_outliers(measurements, method="iqr", threshold=1.5):
    """
    Detect outliers in a set of measurements using the specified method.

    Parameters
    ----------
    measurements : list of float
        Raw measurement values.
    method : str
        Detection method. Currently supports 'iqr' (Interquartile Range).
    threshold : float
        Multiplier for the IQR to determine outlier bounds.

    Returns
    -------
    dict
        Dictionary containing outlier indices, count, bounds, and method used.
    """
    if method != "iqr":
        raise ValueError(f"Unsupported outlier detection method: {method}")

    sorted_data = sorted(measurements)
    n = len(sorted_data)

    q1_idx = n * 0.25
    q3_idx = n * 0.75

    q1 = _interpolate_percentile(sorted_data, q1_idx)
    q3 = _interpolate_percentile(sorted_data, q3_idx)

    iqr = q3 - q1
    lower_bound = q1 - threshold * iqr
    upper_bound = q3 + threshold * iqr

    outlier_indices = []
    for i, val in enumerate(measurements):
        if val < lower_bound or val > upper_bound:
            outlier_indices.append(i)

    return {
        "method": method,
        "threshold": threshold,
        "q1": q1,
        "q3": q3,
        "iqr": iqr,
        "lower_bound": lower_bound,
        "upper_bound": upper_bound,
        "outlier_count": len(outlier_indices),
        "outlier_indices": outlier_indices,
    }


def winsorize_data(measurements, percentile):
    """
    Winsorize measurements by capping extreme values at the specified percentile
    boundaries. Values below the lower percentile are set to the lower bound,
    and values above the upper percentile are set to the upper bound.

    The winsorization boundaries are computed using linear interpolation at the
    given percentile and its complement (100 - percentile).

    Parameters
    ----------
    measurements : list of float
        Raw measurement values to winsorize.
    percentile : float
        The percentile threshold (e.g., 5.0 means cap at 5th and 95th percentiles).

    Returns
    -------
    list of float
        Winsorized measurement values.
    """
    if not measurements:
        return []

    sorted_data = sorted(measurements)
    n = len(sorted_data)

    lower_idx = n * (percentile / 100.0)
    upper_idx = n * ((100.0 - percentile) / 100.0)

    lower_bound = _interpolate_percentile(sorted_data, lower_idx)
    upper_bound = _interpolate_percentile(sorted_data, upper_idx)

    result = []
    for val in measurements:
        if val < lower_bound:
            result.append(lower_bound)
        elif val > upper_bound:
            result.append(upper_bound)
        else:
            result.append(val)

    return result


def preprocess_groups(measurements, normalize=False, center=False):
    """
    Apply preprocessing transformations to a group's measurements.

    Parameters
    ----------
    measurements : list of float
        Input measurement values (possibly already winsorized).
    normalize : bool
        If True, scale values to [0, 1] range using min-max normalization.
    center : bool
        If True, subtract the mean from all values (applied after normalization
        if both are True).

    Returns
    -------
    list of float
        Preprocessed measurement values.
    """
    if not measurements:
        return []

    result = measurements[:]

    if normalize:
        min_val = min(result)
        max_val = max(result)
        range_val = max_val - min_val
        if range_val > 0:
            result = [(x - min_val) / range_val for x in result]
        else:
            result = [0.0 for _ in result]

    if center:
        mean_val = sum(result) / len(result)
        result = [x - mean_val for x in result]

    return result


def compute_trimmed_mean(measurements, trim_fraction=0.1):
    """
    Compute the trimmed mean by removing a fraction of values from each tail.

    Parameters
    ----------
    measurements : list of float
        Input measurement values.
    trim_fraction : float
        Fraction of data to trim from each end (0.1 means 10% from each tail).

    Returns
    -------
    float
        The trimmed mean value.
    """
    if not measurements:
        return 0.0

    sorted_data = sorted(measurements)
    n = len(sorted_data)
    trim_count = int(math.floor(n * trim_fraction))

    if trim_count * 2 >= n:
        return sum(sorted_data) / n

    trimmed = sorted_data[trim_count: n - trim_count]
    return sum(trimmed) / len(trimmed)


def compute_median_absolute_deviation(measurements):
    """
    Compute the Median Absolute Deviation (MAD) of a dataset.

    MAD is a robust measure of statistical dispersion, calculated as the
    median of the absolute deviations from the data's median.

    Parameters
    ----------
    measurements : list of float
        Input measurement values.

    Returns
    -------
    float
        The MAD value.
    """
    if not measurements:
        return 0.0

    sorted_data = sorted(measurements)
    n = len(sorted_data)
    median = _interpolate_percentile(sorted_data, n * 0.5)

    abs_deviations = sorted([abs(x - median) for x in measurements])
    mad = _interpolate_percentile(abs_deviations, len(abs_deviations) * 0.5)

    return mad


def _interpolate_percentile(sorted_data, fractional_index):
    """
    Compute a percentile value using linear interpolation.

    Parameters
    ----------
    sorted_data : list of float
        Sorted data values.
    fractional_index : float
        The fractional index position for interpolation.

    Returns
    -------
    float
        Interpolated percentile value.
    """
    n = len(sorted_data)
    if n == 0:
        return 0.0

    # Clamp to valid range
    if fractional_index <= 0:
        return sorted_data[0]
    if fractional_index >= n - 1:
        return sorted_data[-1]

    lower = int(math.floor(fractional_index))
    upper = lower + 1
    fraction = fractional_index - lower

    return sorted_data[lower] + fraction * (sorted_data[upper] - sorted_data[lower])
