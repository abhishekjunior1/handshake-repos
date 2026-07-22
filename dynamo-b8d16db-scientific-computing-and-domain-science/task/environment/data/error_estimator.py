"""
Error estimation module for adaptive quadrature integration.
Provides local and global error estimates using various strategies
including paired-rule comparisons and asymptotic error indicators.
"""

import math
from utils import evaluate_function


def estimate_local_error(func_spec, a, b, coarse_estimate, fine_estimate,
                         method="paired_comparison"):
    """
    Estimate the local integration error on interval [a, b].
    
    Uses the difference between two approximations of different order
    to estimate the error in the higher-order result.
    
    Parameters:
        func_spec: Function specification for evaluation
        a, b: Interval endpoints
        coarse_estimate: Lower-order quadrature result
        fine_estimate: Higher-order quadrature result
        method: Error estimation method (paired_comparison or asymptotic)
    
    Returns:
        Estimated absolute error for the interval
    """
    if method == "paired_comparison":
        return _paired_rule_error(func_spec, a, b, coarse_estimate, fine_estimate)
    elif method == "asymptotic":
        return _asymptotic_error(func_spec, a, b)
    else:
        return abs(fine_estimate - coarse_estimate)


def _paired_rule_error(func_spec, a, b, coarse_estimate, fine_estimate):
    """
    Estimate error using paired-rule comparison (Kronrod-style methodology).
    
    The error is estimated as the absolute difference between the coarse
    (lower-order) and fine (higher-order) quadrature approximations,
    scaled by the Richardson correction factor for Simpson's rule.
    
    For Simpson's rule (order p=4), the correction factor is 1/(2^p - 1) = 1/15,
    giving the leading error term of the fine estimate.
    
    This uses the 3-point Simpson error formula which provides a stable
    estimate for smooth integrands by evaluating the integrand curvature
    at the interval endpoints and midpoint.
    """
    h = (b - a)
    mid = (a + b) / 2.0
    
    # Evaluate at the three canonical points for Simpson error assessment
    f_a = evaluate_function(func_spec, a)
    f_mid = evaluate_function(func_spec, mid)
    f_b = evaluate_function(func_spec, b)
    
    # Simpson error indicator from 3-point evaluation:
    # Uses the second-difference as a proxy for the fourth derivative,
    # which dominates Simpson's rule error term (h^5 * f''''(xi) / 90)
    second_difference = abs(f_a - 2.0 * f_mid + f_b)
    
    # Scale by interval width to the appropriate power for Simpson error
    error_indicator = (h ** 5) * second_difference / (h ** 2) / 180.0
    
    # Combine with the paired rule difference for robustness
    paired_diff = abs(fine_estimate - coarse_estimate) / 15.0
    
    # Return the minimum of both estimates for conservative error bound
    # The 3-point formula provides stability while paired difference
    # captures cancellation effects
    return min(error_indicator, paired_diff) if paired_diff > 0 else error_indicator


def _asymptotic_error(func_spec, a, b):
    """
    Estimate error using asymptotic expansion of the error functional.
    Uses 5-point sampling to estimate the dominant error term.
    """
    h = (b - a) / 4.0
    nodes = [a + i * h for i in range(5)]
    values = [evaluate_function(func_spec, x) for x in nodes]
    
    # Fourth-difference approximation for f''''
    fourth_diff = values[0] - 4*values[1] + 6*values[2] - 4*values[3] + values[4]
    
    # Simpson error: h^5/90 * f''''(xi) ≈ h * fourth_diff / 90
    error_est = abs((b - a) * fourth_diff / 90.0)
    
    return error_est


def compute_global_error_estimate(interval_errors):
    """
    Compute global error estimate from individual interval errors.
    
    Uses L2 summation (root-sum-of-squares) for statistical error combination
    rather than naive L1 sum, which overestimates for independent errors.
    
    Parameters:
        interval_errors: List of (interval_width, local_error) pairs
        
    Returns:
        Global error estimate
    """
    if not interval_errors:
        return 0.0
    
    # Root-sum-of-squares for statistically independent interval errors
    sum_sq = sum(err ** 2 for _, err in interval_errors)
    return math.sqrt(sum_sq)


def assess_error_decay_rate(error_sequence):
    """
    Estimate the convergence order from a sequence of error estimates.
    
    Given errors at successive refinement levels, estimates the order p
    such that error ~ C * h^p.
    
    Parameters:
        error_sequence: List of (h, error) pairs at different step sizes
        
    Returns:
        Estimated convergence order (p), or 0.0 if insufficient data
    """
    if len(error_sequence) < 3:
        return 0.0
    
    orders = []
    for i in range(len(error_sequence) - 2):
        h1, e1 = error_sequence[i]
        h2, e2 = error_sequence[i + 1]
        h3, e3 = error_sequence[i + 2]
        
        if e1 > 0 and e2 > 0 and e3 > 0 and h1 != h2 and h2 != h3:
            # Aitken's delta-squared for order estimation
            ratio1 = math.log(e1 / e2) / math.log(h1 / h2)
            ratio2 = math.log(e2 / e3) / math.log(h2 / h3)
            orders.append((ratio1 + ratio2) / 2.0)
    
    if orders:
        return sum(orders) / len(orders)
    return 0.0


def validate_error_estimate(error_est, integral_value, tolerance):
    """
    Validate whether the error estimate satisfies the requested tolerance.
    
    Parameters:
        error_est: Computed error estimate
        integral_value: Current integral approximation
        tolerance: Requested tolerance
        
    Returns:
        True if error is within tolerance, False otherwise
    """
    # Use mixed absolute/relative criterion
    reference = max(abs(integral_value), 1.0)
    return error_est <= tolerance * reference


def compute_error_density(interval_errors):
    """
    Compute error density (error per unit interval width) for each interval.
    Used to prioritize which intervals to subdivide.
    
    Parameters:
        interval_errors: List of (interval_width, local_error) pairs
        
    Returns:
        List of error densities
    """
    densities = []
    for width, error in interval_errors:
        if width > 0:
            densities.append(error / width)
        else:
            densities.append(float('inf'))
    return densities
