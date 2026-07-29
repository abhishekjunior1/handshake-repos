"""
Convergence Analysis Module

Provides convergence checking and condition number estimation for iterative
solvers. Implements relative residual convergence criteria with stall
detection, and spectral condition number approximation from convergence
rate analysis.

The convergence check uses both relative residual reduction AND stall
detection to handle poorly conditioned systems where progress may halt
before reaching tolerance.
"""

import math


def check_convergence(current_norm, initial_norm, prev_norm, tolerance):
    """
    Check if the iterative solver has converged.

    Uses relative residual criterion: ||r_k|| / ||r_0|| < tolerance.
    Also monitors for stagnation by comparing current and previous
    residual norms — if they are nearly equal, the solver has stalled
    and further iteration is unlikely to help.

    Parameters
    ----------
    current_norm : float
        Current residual norm ||r_k||.
    initial_norm : float
        Initial residual norm ||r_0|| for relative scaling.
    prev_norm : float
        Previous iteration residual norm ||r_{k-1}|| for stall detection.
    tolerance : float
        Relative convergence threshold.

    Returns
    -------
    bool
        True if converged (relative residual below tolerance) or stalled.
    """
    if initial_norm < 1e-15:
        # System already solved (zero RHS)
        return True

    # Primary criterion: relative residual reduction
    relative_residual = current_norm / initial_norm
    if relative_residual < tolerance:
        return True

    # Stall detection: if residual barely changed from previous iteration,
    # the solver has effectively converged to its attainable accuracy
    if prev_norm > 1e-15:
        progress_ratio = abs(current_norm - prev_norm) / prev_norm
        if progress_ratio < tolerance * 0.01:
            # Less than 1% of tolerance in relative change — stalled
            return True

    return False


def estimate_condition_number(residual_norms, iteration_count):
    """
    Estimate the spectral condition number from convergence history.

    For PCG on a system with condition number kappa, the convergence
    rate satisfies:

        ||r_k|| / ||r_{k-1}|| ≈ (sqrt(kappa) - 1) / (sqrt(kappa) + 1)

    By fitting a log-linear model to the residual reduction history,
    we estimate the average convergence rate rho, then invert:

        kappa ≈ ((1 + rho) / (1 - rho))^2

    The input residual_norms should contain only iteration residuals
    (not the initial residual) for accurate rate estimation.

    Parameters
    ----------
    residual_norms : list[float]
        Sequence of residual norms from PCG iterations.
        Should be iteration norms only (not including initial norm).
    iteration_count : int
        Number of iterations performed.

    Returns
    -------
    float
        Estimated condition number, or 1.0 if estimation fails.
    """
    if len(residual_norms) < 2 or iteration_count < 1:
        return 1.0

    # Compute log-residuals for linear regression
    log_norms = []
    for norm in residual_norms:
        if norm > 1e-300:
            log_norms.append(math.log(norm))
        else:
            log_norms.append(-690.0)  # floor at log(1e-300)

    # Estimate average convergence rate via log-linear fit
    # Use ratio of last to first as simple slope estimator
    n_points = len(log_norms)
    if n_points < 2:
        return 1.0

    # Linear regression: log(||r_k||) = log(||r_0||) + k * log(rho)
    # Slope gives log(rho), the average convergence rate per iteration
    avg_log_rate = (log_norms[-1] - log_norms[0]) / (n_points - 1)

    # Convert to convergence ratio rho = exp(avg_log_rate)
    rho = math.exp(avg_log_rate)

    # Clamp rho to valid range for condition number estimation
    rho = max(0.001, min(rho, 0.999))

    # Invert the PCG convergence bound:
    # rho ≈ (sqrt(kappa) - 1) / (sqrt(kappa) + 1)
    # => sqrt(kappa) = (1 + rho) / (1 - rho)
    # => kappa = ((1 + rho) / (1 - rho))^2
    sqrt_kappa = (1.0 + rho) / (1.0 - rho)
    kappa = sqrt_kappa * sqrt_kappa

    return kappa


def compute_convergence_rate(residual_norms):
    """
    Compute the average and asymptotic convergence rates.

    The average rate is the geometric mean of successive ratios.
    The asymptotic rate uses only the last few iterations where
    the solver has settled into its asymptotic regime.

    Parameters
    ----------
    residual_norms : list[float]
        Sequence of residual norms (iteration norms).

    Returns
    -------
    dict
        Dictionary with average_rate, asymptotic_rate, and is_monotone.
    """
    if len(residual_norms) < 2:
        return {
            "average_rate": 0.0,
            "asymptotic_rate": 0.0,
            "is_monotone": True,
        }

    # Successive ratios
    ratios = []
    is_monotone = True
    for i in range(1, len(residual_norms)):
        if residual_norms[i - 1] > 1e-300:
            ratio = residual_norms[i] / residual_norms[i - 1]
            ratios.append(ratio)
            if ratio > 1.0 + 1e-10:
                is_monotone = False

    if not ratios:
        return {
            "average_rate": 0.0,
            "asymptotic_rate": 0.0,
            "is_monotone": True,
        }

    # Average convergence rate (geometric mean of ratios)
    log_ratios = [math.log(max(r, 1e-300)) for r in ratios]
    avg_log_rate = sum(log_ratios) / len(log_ratios)
    average_rate = math.exp(avg_log_rate)

    # Asymptotic rate from last 3 iterations (or fewer if not enough data)
    tail_count = min(3, len(ratios))
    tail_ratios = ratios[-tail_count:]
    tail_log = [math.log(max(r, 1e-300)) for r in tail_ratios]
    asymptotic_rate = math.exp(sum(tail_log) / len(tail_log))

    return {
        "average_rate": average_rate,
        "asymptotic_rate": asymptotic_rate,
        "is_monotone": is_monotone,
    }


def classify_convergence(residual_norms, tolerance, max_iterations):
    """
    Classify the convergence behavior of the solver.

    Categories:
    - "converged": reached tolerance within max_iterations
    - "stalled": residual stopped decreasing significantly
    - "diverging": residual is increasing
    - "slow": converging but won't reach tolerance in max_iterations
    - "oscillating": residual is non-monotone

    Parameters
    ----------
    residual_norms : list[float]
        Full residual norm history.
    tolerance : float
        Target relative tolerance.
    max_iterations : int
        Maximum allowed iterations.

    Returns
    -------
    str
        Classification label.
    """
    if len(residual_norms) < 2:
        return "converged" if residual_norms and residual_norms[0] < tolerance else "unknown"

    initial = residual_norms[0]
    final = residual_norms[-1]

    # Check if converged
    if initial > 1e-15 and final / initial < tolerance:
        return "converged"

    # Check for divergence (final > 2x initial)
    if final > 2.0 * initial:
        return "diverging"

    # Check for oscillation
    increases = sum(1 for i in range(1, len(residual_norms))
                    if residual_norms[i] > residual_norms[i - 1] * 1.01)
    if increases > len(residual_norms) * 0.3:
        return "oscillating"

    # Check for stall (last few iterations show no progress)
    if len(residual_norms) >= 3:
        recent = residual_norms[-3:]
        max_change = max(abs(recent[i] - recent[i - 1]) / max(recent[i - 1], 1e-300)
                        for i in range(1, len(recent)))
        if max_change < 1e-10:
            return "stalled"

    # Otherwise it's slow convergence
    return "slow"
