"""
Residual analysis for harmonic decomposition quality assessment.

Evaluates whether the residuals after harmonic and trend extraction
are consistent with white noise. If significant autocorrelation
remains, the decomposition is incomplete.

The scoring function normalizes residual statistics by the effective
sample size to produce comparable scores across different window
configurations.
"""

import math


def analyze_residuals(residuals, n_effective):
    """Analyze residual series for remaining structure.

    Computes autocorrelation-based statistics to assess whether
    the residuals are consistent with white noise.

    Args:
        residuals: Residual series after decomposition.
        n_effective: Effective sample size (accounts for windowing).

    Returns:
        Dictionary with residual diagnostics.
    """
    n = len(residuals)
    if n < 5:
        return _empty_diagnostics()

    # Residual statistics
    res_mean = sum(residuals) / n
    res_var = sum((r - res_mean) ** 2 for r in residuals) / n

    # Autocorrelation at lags 1..max_lag
    max_lag = min(10, n // 4)
    acf = compute_residual_acf(residuals, max_lag)

    # Ljung-Box portmanteau statistic
    lb_stat = compute_ljung_box(acf, n)

    # Runs test for randomness
    n_runs, expected_runs = compute_runs_test(residuals)

    return {
        'residual_mean': round(res_mean, 6),
        'residual_variance': round(res_var, 6),
        'autocorrelations': [round(a, 6) for a in acf],
        'ljung_box_statistic': round(lb_stat, 6),
        'n_runs': n_runs,
        'expected_runs': round(expected_runs, 6),
        'max_lag_tested': max_lag
    }


def score_decomposition(residuals, harmonic_power, n_effective):
    """Score the overall decomposition quality.

    The decomposition score combines:
    1. Signal-to-noise ratio (harmonic power vs residual power)
    2. Residual whiteness (low autocorrelation = good)
    3. Normalization by effective sample size for comparability

    The normalization by n_effective is essential: windowed observations
    have fewer effective degrees of freedom, so the same residual
    autocorrelation is MORE significant (less likely under white noise)
    with smaller n_effective.

    Score formula:
        snr_score = harmonic_power / (residual_variance * n_effective)
        whiteness = 1 - max_abs_autocorrelation
        quality = snr_score * whiteness

    Args:
        residuals: Residual series after decomposition.
        harmonic_power: Total power in extracted harmonics.
        n_effective: Effective degrees of freedom.

    Returns:
        Dictionary with quality scores.
    """
    n = len(residuals)
    if n < 3:
        return {'snr_score': 0.0, 'whiteness_score': 0.0, 'overall_quality': 0.0}

    res_mean = sum(residuals) / n
    res_var = sum((r - res_mean) ** 2 for r in residuals) / n

    # Signal-to-noise: normalize by effective DoF
    if res_var > 0 and n_effective > 0:
        snr_score = harmonic_power / (res_var * n_effective)
    else:
        snr_score = 0.0

    # Whiteness: based on residual autocorrelation
    max_lag = min(5, n // 4)
    acf = compute_residual_acf(residuals, max_lag)
    if acf:
        max_abs_acf = max(abs(a) for a in acf)
        whiteness = 1.0 - min(1.0, max_abs_acf)
    else:
        whiteness = 1.0

    # Combined quality
    overall = snr_score * whiteness

    return {
        'snr_score': round(snr_score, 6),
        'whiteness_score': round(whiteness, 6),
        'overall_quality': round(overall, 6)
    }


def compute_residual_acf(residuals, max_lag):
    """Compute sample autocorrelation function of residuals.

    Uses the biased estimator (divide by n) for positive-definiteness.

    Args:
        residuals: Residual series.
        max_lag: Maximum lag to compute.

    Returns:
        List of autocorrelation values at lags 1..max_lag.
    """
    n = len(residuals)
    mean = sum(residuals) / n
    centered = [r - mean for r in residuals]
    r0 = sum(c * c for c in centered) / n

    if r0 == 0:
        return [0.0] * max_lag

    acf = []
    for k in range(1, max_lag + 1):
        rk = sum(centered[t] * centered[t - k] for t in range(k, n)) / n
        acf.append(rk / r0)

    return acf


def compute_ljung_box(acf, n):
    """Compute Ljung-Box Q statistic.

    Q = n*(n+2) * sum(rho_k^2 / (n-k))

    Args:
        acf: Autocorrelation values at lags 1..K.
        n: Sample size.

    Returns:
        Q statistic value.
    """
    q = 0.0
    for k, rho in enumerate(acf, 1):
        if n - k > 0:
            q += (rho ** 2) / (n - k)
    q *= n * (n + 2)
    return q


def compute_runs_test(residuals):
    """Compute runs test for randomness.

    Counts the number of runs (consecutive sequences above/below median)
    and compares to expected value under randomness.

    Args:
        residuals: Residual series.

    Returns:
        Tuple of (observed_runs, expected_runs).
    """
    n = len(residuals)
    if n < 3:
        return 0, 0.0

    median = sorted(residuals)[n // 2]

    # Count runs
    above = [r > median for r in residuals]
    runs = 1
    for t in range(1, n):
        if above[t] != above[t - 1]:
            runs += 1

    # Expected runs under randomness
    n_above = sum(1 for a in above if a)
    n_below = n - n_above

    if n_above > 0 and n_below > 0:
        expected = 1.0 + 2.0 * n_above * n_below / n
    else:
        expected = 1.0

    return runs, expected


def _empty_diagnostics():
    """Return empty diagnostics for degenerate cases."""
    return {
        'residual_mean': 0.0,
        'residual_variance': 0.0,
        'autocorrelations': [],
        'ljung_box_statistic': 0.0,
        'n_runs': 0,
        'expected_runs': 0.0,
        'max_lag_tested': 0
    }
