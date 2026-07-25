"""
Harmonic model fitting for time series decomposition.

Fits a sum-of-sinusoids model to the time series given detected
frequencies. Estimates amplitude and phase for each harmonic
component via least-squares regression against the basis functions.

The model:
    x(t) = sum_k A_k * cos(2*pi*f_k*t + phi_k) + trend(t) + epsilon(t)
"""

import math


def fit_harmonic_model(series, frequencies, window_weights):
    """Fit harmonic model to the series at detected frequencies.

    Uses weighted least-squares with the observation window as weights
    to estimate amplitude and phase for each harmonic.

    Args:
        series: Original time series.
        frequencies: List of detected frequencies.
        window_weights: Observation weights from windowing.

    Returns:
        Dictionary with:
            - amplitudes: list of fitted amplitudes per harmonic
            - phases: list of fitted phases per harmonic
            - fitted_values: reconstructed harmonic signal
            - residuals: series minus fitted harmonics
            - total_harmonic_power: sum of squared amplitudes
    """
    n = len(series)
    n_harmonics = len(frequencies)

    if n_harmonics == 0:
        return {
            'amplitudes': [],
            'phases': [],
            'fitted_values': [0.0] * n,
            'residuals': list(series),
            'total_harmonic_power': 0.0
        }

    # Build design matrix: [cos(2*pi*f1*t), sin(2*pi*f1*t), ...]
    # Solve weighted least squares for each frequency pair
    amplitudes = []
    phases = []
    fitted = [0.0] * n

    residual = list(series)

    for freq in frequencies:
        # Weighted least-squares fit for this frequency
        a, b = fit_single_harmonic(residual, freq, window_weights)

        # Convert to amplitude and phase
        amplitude = math.sqrt(a * a + b * b)
        phase = math.atan2(-b, a)

        amplitudes.append(round(amplitude, 6))
        phases.append(round(phase, 6))

        # Add to fitted values and subtract from residual
        for t in range(n):
            component = a * math.cos(2 * math.pi * freq * t) + \
                        b * math.sin(2 * math.pi * freq * t)
            fitted[t] += component
            residual[t] -= component

    total_power = sum(a ** 2 for a in amplitudes)

    return {
        'amplitudes': amplitudes,
        'phases': phases,
        'fitted_values': [round(f, 6) for f in fitted],
        'residuals': [round(r, 6) for r in residual],
        'total_harmonic_power': round(total_power, 6)
    }


def fit_single_harmonic(series, frequency, weights):
    """Fit a single harmonic component via weighted least squares.

    Estimates coefficients a, b in:
        x(t) ≈ a*cos(2*pi*f*t) + b*sin(2*pi*f*t)

    using observation weights.

    Args:
        series: Current residual series.
        frequency: Target frequency.
        weights: Observation weights.

    Returns:
        Tuple (a, b) of cosine and sine coefficients.
    """
    n = len(series)

    # Weighted normal equations
    wcc = 0.0  # sum(w * cos^2)
    wss = 0.0  # sum(w * sin^2)
    wcs = 0.0  # sum(w * cos * sin)
    wxc = 0.0  # sum(w * x * cos)
    wxs = 0.0  # sum(w * x * sin)

    for t in range(n):
        w = weights[t]
        c = math.cos(2 * math.pi * frequency * t)
        s = math.sin(2 * math.pi * frequency * t)

        wcc += w * c * c
        wss += w * s * s
        wcs += w * c * s
        wxc += w * series[t] * c
        wxs += w * series[t] * s

    # Solve 2x2 weighted normal equations
    det = wcc * wss - wcs * wcs
    if abs(det) < 1e-15:
        return 0.0, 0.0

    a = (wss * wxc - wcs * wxs) / det
    b = (wcc * wxs - wcs * wxc) / det

    return a, b


def compute_harmonic_contribution(amplitudes, series_variance):
    """Compute the fraction of variance explained by harmonics.

    Args:
        amplitudes: List of harmonic amplitudes.
        series_variance: Total series variance.

    Returns:
        Fraction of variance explained (0 to 1).
    """
    if series_variance <= 0:
        return 0.0

    harmonic_power = sum(a ** 2 for a in amplitudes) / 2.0
    return min(1.0, harmonic_power / series_variance)


def extrapolate_harmonics(frequencies, amplitudes, phases, horizon, n_history):
    """Extrapolate harmonic components beyond the observed series.

    Args:
        frequencies: Detected frequencies.
        amplitudes: Fitted amplitudes.
        phases: Fitted phases.
        horizon: Number of steps to extrapolate.
        n_history: Length of historical series (for time indexing).

    Returns:
        List of extrapolated harmonic values.
    """
    extrapolated = []
    for h in range(horizon):
        t = n_history + h
        value = 0.0
        for k in range(len(frequencies)):
            value += amplitudes[k] * math.cos(
                2 * math.pi * frequencies[k] * t + phases[k]
            )
        extrapolated.append(round(value, 6))

    return extrapolated
