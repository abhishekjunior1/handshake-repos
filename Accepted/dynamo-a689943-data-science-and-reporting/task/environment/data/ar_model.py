"""AR Model module for the anomaly detection pipeline.

Fits autoregressive (AR) spectral envelope models using the
Levinson-Durbin recursion on estimated autocorrelation sequences.
The AR spectral envelope provides a smooth parametric estimate of
the spectral density, used as the baseline for anomaly scoring.

The AR(p) spectral density is:
    S_AR(f) = sigma^2 / |A(e^{j*2*pi*f})|^2

where A(z) = 1 - sum_{k=1}^{p} a_k * z^{-k} is the AR polynomial
and sigma^2 is the innovation variance.
"""

import math
from typing import List, Tuple, Dict, Optional


class ARModelError(Exception):
    """Raised when AR model fitting encounters an error."""
    pass


def compute_autocorrelation(series: List[float], max_lag: int) -> List[float]:
    """Compute biased autocorrelation estimates up to max_lag.

    Uses the biased estimator R(k) = (1/N) * sum_{t=0}^{N-k-1} x(t)*x(t+k)
    which guarantees a positive-definite Toeplitz matrix for Levinson-Durbin.

    Args:
        series: Zero-mean time series.
        max_lag: Maximum lag to compute.

    Returns:
        List of autocorrelation values R(0), R(1), ..., R(max_lag).
    """
    n = len(series)
    if max_lag >= n:
        raise ARModelError(f"max_lag ({max_lag}) must be < series length ({n})")

    acf = []
    for k in range(max_lag + 1):
        r_k = 0.0
        for t in range(n - k):
            r_k += series[t] * series[t + k]
        r_k /= n  # Biased estimator
        acf.append(r_k)

    return acf


def levinson_durbin(acf: List[float], order: int) -> Tuple[List[float], float]:
    """Solve the Yule-Walker equations via Levinson-Durbin recursion.

    Efficiently computes the AR coefficients for the given autocorrelation
    sequence without forming the full Toeplitz matrix.

    Args:
        acf: Autocorrelation sequence R(0), R(1), ..., R(order).
        order: AR model order p.

    Returns:
        Tuple of (ar_coefficients, innovation_variance).
        ar_coefficients is [a_1, a_2, ..., a_p].
    """
    if order <= 0:
        raise ARModelError("AR order must be positive")
    if len(acf) < order + 1:
        raise ARModelError("Insufficient autocorrelation values")
    if acf[0] <= 0:
        raise ARModelError("R(0) must be positive (non-zero variance)")

    # Initialize
    a = [0.0] * (order + 1)
    sigma2 = acf[0]

    a_prev = [0.0] * (order + 1)

    for m in range(1, order + 1):
        # Compute reflection coefficient
        numerator = acf[m]
        for k in range(1, m):
            numerator -= a_prev[k] * acf[m - k]

        if sigma2 == 0:
            raise ARModelError("Degenerate autocorrelation (sigma2 = 0)")

        reflection = numerator / sigma2

        # Check stability
        if abs(reflection) >= 1.0:
            # Clip to maintain stability
            reflection = 0.99 * (1.0 if reflection > 0 else -1.0)

        # Update coefficients
        a[m] = reflection
        for k in range(1, m):
            a[k] = a_prev[k] - reflection * a_prev[m - k]

        # Update innovation variance
        sigma2 = sigma2 * (1.0 - reflection * reflection)

        # Store for next iteration
        a_prev = a[:]

    return a[1:order + 1], sigma2


def compute_ar_spectrum(ar_coeffs: List[float], sigma2: float,
                        frequencies: List[float]) -> List[float]:
    """Evaluate the AR spectral density at given frequencies.

    Computes S_AR(f) = sigma^2 / |A(e^{j*f})|^2 where
    A(z) = 1 - sum_{k=1}^{p} a_k * z^{-k}.

    Args:
        ar_coeffs: AR coefficients [a_1, ..., a_p].
        sigma2: Innovation variance.
        frequencies: Angular frequencies at which to evaluate.

    Returns:
        List of AR spectral density values.
    """
    spectrum = []
    for f in frequencies:
        # Compute A(e^{j*f}) = 1 - sum a_k * e^{-j*k*f}
        real_part = 1.0
        imag_part = 0.0
        for k, a_k in enumerate(ar_coeffs, start=1):
            real_part -= a_k * math.cos(k * f)
            imag_part += a_k * math.sin(k * f)

        # |A(e^{j*f})|^2
        mag_squared = real_part * real_part + imag_part * imag_part

        if mag_squared < 1e-12:
            mag_squared = 1e-12  # Prevent division by zero

        s_ar = sigma2 / mag_squared
        spectrum.append(s_ar)

    return spectrum


def fit_ar_model(series: List[float], order: int) -> Dict[str, object]:
    """Fit an AR model to a time series segment.

    Estimates the AR spectral envelope by:
    1. Computing biased autocorrelation
    2. Solving Yule-Walker via Levinson-Durbin
    3. Evaluating the parametric spectrum

    Args:
        series: Input time series (will be demeaned internally).
        order: AR model order.

    Returns:
        Dictionary with:
            'coefficients': AR coefficients
            'sigma2': innovation variance
            'order': model order
            'aic': Akaike Information Criterion for model selection
    """
    n = len(series)
    if n < order + 2:
        raise ARModelError(f"Series too short ({n}) for AR order {order}")

    # Demean the series
    mean_val = sum(series) / n
    demeaned = [x - mean_val for x in series]

    # Compute autocorrelation
    acf = compute_autocorrelation(demeaned, order)

    # Fit via Levinson-Durbin
    coeffs, sigma2 = levinson_durbin(acf, order)

    # Compute AIC for model selection
    # AIC = n * ln(sigma2) + 2*p
    if sigma2 > 0:
        aic = n * math.log(sigma2) + 2.0 * order
    else:
        aic = float('inf')

    return {
        'coefficients': coeffs,
        'sigma2': sigma2,
        'order': order,
        'aic': aic,
        'mean': mean_val
    }


def select_ar_order(series: List[float], max_order: int = 20) -> int:
    """Select optimal AR order using AIC.

    Fits AR models of increasing order and selects the one
    with minimum AIC, balancing fit and complexity.

    Args:
        series: Input time series.
        max_order: Maximum order to consider.

    Returns:
        Optimal AR model order.
    """
    n = len(series)
    max_feasible = min(max_order, n // 3)

    if max_feasible < 1:
        return 1

    best_order = 1
    best_aic = float('inf')

    for p in range(1, max_feasible + 1):
        try:
            result = fit_ar_model(series, p)
            if result['aic'] < best_aic:
                best_aic = result['aic']
                best_order = p
        except ARModelError:
            continue

    return best_order
