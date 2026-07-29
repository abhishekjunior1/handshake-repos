"""
Block maxima extraction and GEV distribution fitting module.

Implements the block maxima method for extracting annual/seasonal maxima
from the observation series and fits a Generalized Extreme Value (GEV)
distribution using probability-weighted moments (PWM) estimation.
"""

import math
from typing import List, Dict, Tuple


def extract_block_maxima(observations: List[float], block_size: int) -> List[float]:
    """
    Extract block maxima from the observation series.

    Divides the series into non-overlapping blocks of specified size
    and extracts the maximum value from each complete block.

    Parameters
    ----------
    observations : list of float
        Complete observation time series.
    block_size : int
        Number of observations per block.

    Returns
    -------
    list of float
        Maximum values from each complete block.
    """
    n = len(observations)
    n_blocks = n // block_size
    maxima = []

    for i in range(n_blocks):
        start = i * block_size
        end = start + block_size
        block = observations[start:end]
        maxima.append(max(block))

    return maxima


def compute_block_summary(block_maxima: List[float]) -> Dict[str, float]:
    """
    Compute summary statistics for block maxima series.

    Parameters
    ----------
    block_maxima : list of float
        Extracted block maximum values.

    Returns
    -------
    dict
        Summary statistics: count, mean, max, min, std.
    """
    n = len(block_maxima)
    mean_val = sum(block_maxima) / n
    variance = sum((x - mean_val) ** 2 for x in block_maxima) / (n - 1)
    std_val = math.sqrt(variance)

    return {
        "count": n,
        "mean": round(mean_val, 4),
        "max": round(max(block_maxima), 4),
        "min": round(min(block_maxima), 4),
        "std": round(std_val, 4),
    }


def _compute_pwm(sorted_data: List[float]) -> Tuple[float, float, float]:
    """
    Compute probability-weighted moments (b0, b1, b2) for GEV estimation.

    Uses unbiased PWM estimators following Hosking et al. (1985).

    Parameters
    ----------
    sorted_data : list of float
        Block maxima sorted in ascending order.

    Returns
    -------
    tuple of (float, float, float)
        PWM coefficients b0, b1, b2.
    """
    n = len(sorted_data)
    b0 = sum(sorted_data) / n
    b1 = sum(i * sorted_data[i] for i in range(n)) / (n * (n - 1))
    b2 = sum(i * (i - 1) * sorted_data[i] for i in range(n)) / (n * (n - 1) * (n - 2))
    return b0, b1, b2


def fit_gev(block_maxima: List[float]) -> Dict[str, float]:
    """
    Fit GEV distribution to block maxima using PWM method.

    Estimates location (mu), scale (sigma), and shape (xi) parameters
    of the Generalized Extreme Value distribution via L-moments derived
    from probability-weighted moments.

    Parameters
    ----------
    block_maxima : list of float
        Extracted block maximum values.

    Returns
    -------
    dict
        GEV parameters: location, scale, shape.
    """
    sorted_data = sorted(block_maxima)
    n = len(sorted_data)

    # Compute L-moments from PWMs
    b0, b1, b2 = _compute_pwm(sorted_data)

    L1 = b0
    L2 = 2 * b1 - b0
    L3 = 6 * b2 - 6 * b1 + b0

    # L-moment ratio (L-skewness)
    tau3 = L3 / L2

    # Approximate shape parameter from L-skewness
    # Using rational approximation (Hosking 1997)
    c = 2.0 / (3.0 + tau3) - math.log(2.0) / math.log(3.0)
    shape = 7.8590 * c + 2.9554 * c * c

    # Constrain shape to reasonable range for environmental data
    shape = max(min(shape, 0.5), -0.5)

    # Derive scale and location from shape and L-moments
    if abs(shape) < 1e-8:
        # Gumbel case (shape -> 0)
        scale = L2 / math.log(2.0)
        location = L1 - 0.5772 * scale
    else:
        gamma_val = math.gamma(1 + shape)
        scale = (L2 * shape) / (gamma_val * (1 - 2 ** (-shape)))
        location = L1 - scale * (gamma_val - 1) / shape

    return {
        "location": round(location, 6),
        "scale": round(abs(scale), 6),
        "shape": round(shape, 6),
    }
