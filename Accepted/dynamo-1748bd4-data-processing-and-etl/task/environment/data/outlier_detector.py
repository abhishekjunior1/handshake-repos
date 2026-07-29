"""
Outlier Detection Module
========================

Implements outlier detection using the Modified Z-Score method based on
the Median Absolute Deviation (MAD). This approach is more robust than
standard z-scores because it uses the median rather than the mean,
making it resistant to the very outliers it aims to detect.

The Modified Z-Score is defined as:
    M_i = 0.6745 * (x_i - median) / MAD

where MAD = median(|x_i - median|) and 0.6745 is the 0.75th quantile
of the standard normal distribution (consistency constant).

Values with |M_i| > threshold are classified as outliers. The default
threshold of 3.5 is recommended by Iglewicz and Hoaglin (1993).

Outlier adjustment clamps detected outliers to the threshold boundary
rather than removing them, preserving record count while limiting the
influence of extreme values on downstream aggregations.
"""

import math
from typing import List, Dict, Any, Tuple, Optional


# The consistency constant that makes MAD comparable to standard deviation
# for normally distributed data. Equal to 1/Q(0.75) where Q is the quantile
# function of the standard normal distribution.
CONSISTENCY_CONSTANT = 0.6745

# Default threshold for the modified z-score beyond which values are
# considered outliers. Based on Iglewicz and Hoaglin (1993) recommendation.
DEFAULT_THRESHOLD = 3.5

# Minimum MAD value to prevent division by zero in datasets with very
# low dispersion around the median.
MIN_MAD = 1e-10


def compute_median(values: List[float]) -> float:
    """
    Compute the median of a list of numeric values.

    Parameters
    ----------
    values : List[float]
        Numeric values. Must not be empty.

    Returns
    -------
    float
        The median value.
    """
    sorted_vals = sorted(values)
    n = len(sorted_vals)
    if n % 2 == 0:
        return (sorted_vals[n // 2 - 1] + sorted_vals[n // 2]) / 2.0
    else:
        return sorted_vals[n // 2]


def compute_mad(values: List[float]) -> float:
    """
    Compute the Median Absolute Deviation (MAD) for a dataset.

    MAD = median(|x_i - median(x)|)

    MAD is a robust measure of dispersion that is not affected by
    extreme values, making it ideal for outlier detection.

    Parameters
    ----------
    values : List[float]
        Numeric values for which to compute MAD.

    Returns
    -------
    float
        The MAD value. Returns MIN_MAD if computed MAD is zero.
    """
    if not values:
        return MIN_MAD

    median_val = compute_median(values)
    absolute_deviations = [abs(x - median_val) for x in values]
    mad = compute_median(absolute_deviations)

    return max(mad, MIN_MAD)


def compute_modified_z_scores(values: List[float]) -> List[float]:
    """
    Compute Modified Z-Scores for all values in the dataset.

    The Modified Z-Score uses MAD instead of standard deviation:
        M_i = 0.6745 * (x_i - median) / MAD

    Parameters
    ----------
    values : List[float]
        Numeric values to score.

    Returns
    -------
    List[float]
        Modified Z-Scores for each value, maintaining original order.
    """
    if not values:
        return []

    median_val = compute_median(values)
    mad = compute_mad(values)

    modified_z_scores = []
    for x in values:
        mz = CONSISTENCY_CONSTANT * (x - median_val) / mad
        modified_z_scores.append(mz)

    return modified_z_scores


def detect_outliers(values: List[float],
                    threshold: float = DEFAULT_THRESHOLD
                    ) -> Tuple[List[bool], List[float]]:
    """
    Detect outliers using the Modified Z-Score method and return adjusted values.

    Outliers are identified as values whose absolute Modified Z-Score exceeds
    the threshold. Adjusted values clamp outliers to the boundary defined by
    the threshold, preserving the direction (sign) of the deviation.

    The clamping formula for outlier x_i with Modified Z-Score M_i:
        if |M_i| > threshold:
            x_adjusted = median + (threshold / 0.6745) * MAD * sign(M_i)

    Parameters
    ----------
    values : List[float]
        Numeric values to check for outliers.
    threshold : float, optional
        Modified Z-Score threshold. Default is 3.5.

    Returns
    -------
    Tuple[List[bool], List[float]]
        A tuple of (outlier_mask, adjusted_values) where:
        - outlier_mask[i] is True if values[i] is an outlier
        - adjusted_values[i] is the clamped value if outlier, else original
    """
    if not values:
        return [], []

    median_val = compute_median(values)
    mad = compute_mad(values)
    modified_z_scores = compute_modified_z_scores(values)

    outlier_mask = []
    adjusted_values = []

    for i, (val, mz) in enumerate(zip(values, modified_z_scores)):
        is_outlier = abs(mz) > threshold
        outlier_mask.append(is_outlier)

        if is_outlier:
            # Clamp to threshold boundary while preserving direction
            sign = 1.0 if mz > 0 else -1.0
            boundary = median_val + (threshold / CONSISTENCY_CONSTANT) * mad * sign
            adjusted_values.append(boundary)
        else:
            adjusted_values.append(val)

    return outlier_mask, adjusted_values


def detect_outliers_in_records(records: List[Dict[str, Any]],
                               value_field: str,
                               threshold: float = DEFAULT_THRESHOLD
                               ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    """
    Apply outlier detection to a list of records on a specified field.

    Augments each record with outlier detection metadata and returns
    summary statistics about the detection results.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        Input records containing the value field to analyze.
    value_field : str
        The field name to perform outlier detection on.
    threshold : float, optional
        Modified Z-Score threshold for outlier classification.

    Returns
    -------
    Tuple[List[Dict[str, Any]], Dict[str, Any]]
        A tuple of (augmented_records, detection_summary) where:
        - Each record gains 'is_outlier', 'modified_z_score', and
          'adjusted_{value_field}' fields.
        - detection_summary contains counts and statistics.
    """
    values = [float(r[value_field]) for r in records]
    outlier_mask, adjusted_values = detect_outliers(values, threshold)
    modified_z_scores = compute_modified_z_scores(values)

    augmented_records = []
    outlier_count = 0

    for i, record in enumerate(records):
        augmented = dict(record)
        augmented["is_outlier"] = outlier_mask[i]
        augmented["modified_z_score"] = modified_z_scores[i]
        augmented[f"adjusted_{value_field}"] = adjusted_values[i]

        if outlier_mask[i]:
            outlier_count += 1

        augmented_records.append(augmented)

    detection_summary = {
        "total_records": len(records),
        "outlier_count": outlier_count,
        "outlier_rate": outlier_count / len(records) if records else 0.0,
        "threshold_used": threshold,
        "median": compute_median(values) if values else 0.0,
        "mad": compute_mad(values) if values else 0.0
    }

    return augmented_records, detection_summary
