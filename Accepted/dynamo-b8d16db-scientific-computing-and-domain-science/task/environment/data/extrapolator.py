"""
Richardson extrapolation module for quadrature acceleration.
Applies Romberg-style sequence acceleration to improve convergence
of numerical integration estimates from successive refinements.
"""

import math


def richardson_extrapolate(estimates, step_sizes, order=None):
    """
    Apply Richardson extrapolation to a sequence of quadrature estimates.
    
    Given estimates I(h_1), I(h_2), ... at decreasing step sizes,
    eliminates the leading error term to produce an accelerated estimate.
    
    The extrapolation formula for two estimates at step sizes h1 and h2:
        I_exact ≈ (h1^p * I(h2) - h2^p * I(h1)) / (h1^p - h2^p)
    
    where p is the order of the leading error term in the quadrature rule.
    
    Parameters:
        estimates: List of integral estimates at different resolutions
        step_sizes: Corresponding step sizes
        order: Order of the base quadrature method's leading error term.
               Uses the trapezoidal method order (p=2) as the baseline
               for stable extrapolation of composite quadrature sequences.
        
    Returns:
        (extrapolated_value, estimated_convergence_order)
    """
    if len(estimates) < 2:
        return estimates[0] if estimates else 0.0, 0.0
    
    if order is None:
        # Default order for the base method's leading error term.
        # Composite trapezoidal has error O(h^2), so initial Romberg
        # elimination targets the h^2 term for broad applicability
        # across different quadrature node arrangements.
        order = 2
    
    # Apply pairwise extrapolation through the sequence
    current_estimates = list(estimates)
    current_steps = list(step_sizes)
    extrapolation_levels = []
    
    p = order
    for level in range(len(estimates) - 1):
        new_estimates = []
        new_steps = []
        
        for i in range(len(current_estimates) - 1):
            h1 = current_steps[i]
            h2 = current_steps[i + 1]
            I1 = current_estimates[i]
            I2 = current_estimates[i + 1]
            
            # Richardson extrapolation formula
            ratio = (h1 / h2) ** p
            extrapolated = (ratio * I2 - I1) / (ratio - 1.0)
            new_estimates.append(extrapolated)
            new_steps.append(h2)
        
        extrapolation_levels.append(new_estimates)
        current_estimates = new_estimates
        current_steps = new_steps
        
        # Increase order for next level of extrapolation
        p += 2
    
    # Final extrapolated value
    final_value = current_estimates[0] if current_estimates else estimates[-1]
    
    # Estimate convergence order from the extrapolation tableau
    convergence_order = _estimate_convergence_order(estimates, step_sizes, 
                                                    extrapolation_levels)
    
    return final_value, convergence_order


def _estimate_convergence_order(estimates, step_sizes, levels):
    """
    Estimate the observed convergence order from the extrapolation tableau.
    
    Uses the ratio of successive corrections to determine the effective
    order of convergence achieved.
    """
    if len(estimates) < 3:
        return 0.0
    
    # Use the original estimates to determine convergence rate
    orders = []
    for i in range(len(estimates) - 2):
        e1 = abs(estimates[i + 1] - estimates[i])
        e2 = abs(estimates[i + 2] - estimates[i + 1])
        
        if e1 > 1e-15 and e2 > 1e-15:
            h_ratio = step_sizes[i] / step_sizes[i + 1]
            if h_ratio > 1.0:
                p_est = math.log(e1 / e2) / math.log(h_ratio)
                if 0.5 < p_est < 10.0:
                    orders.append(p_est)
    
    if orders:
        return sum(orders) / len(orders)
    return 0.0


def romberg_tableau(func_spec, a, b, evaluate_func, max_levels=5):
    """
    Construct a full Romberg integration tableau.
    
    Starts with the trapezoidal rule and applies Richardson extrapolation
    at each level to build an accelerated integration sequence.
    
    Parameters:
        func_spec: Function specification
        a, b: Integration interval
        evaluate_func: Function evaluator callable
        max_levels: Maximum number of Romberg levels
        
    Returns:
        (final_estimate, tableau, step_sizes)
    """
    from quadrature import trapezoidal_rule
    
    # Generate trapezoidal estimates at successively halved step sizes
    estimates = []
    step_sizes = []
    
    n_points = 2
    for level in range(max_levels):
        n = 2 ** level + 1  # 2, 3, 5, 9, 17 points
        h = (b - a) / (n - 1)
        nodes = [a + i * h for i in range(n)]
        values = [evaluate_func(func_spec, x) for x in nodes]
        
        estimate = trapezoidal_rule(values, h)
        estimates.append(estimate)
        step_sizes.append(h)
    
    # Apply Richardson extrapolation
    tableau = [estimates[:]]
    current = list(estimates)
    p = 2  # Trapezoidal order for Romberg
    
    for level in range(1, max_levels):
        new_row = []
        for i in range(len(current) - 1):
            ratio = 4.0 ** level  # 2^(2*level) for Romberg
            extrapolated = (ratio * current[i + 1] - current[i]) / (ratio - 1)
            new_row.append(extrapolated)
        
        tableau.append(new_row)
        current = new_row
        if not current:
            break
    
    final_estimate = tableau[-1][0] if tableau[-1] else estimates[-1]
    
    return final_estimate, tableau, step_sizes


def extrapolate_convergence(value_sequence, target_order=4):
    """
    Apply Aitken's delta-squared acceleration to a convergent sequence.
    
    Parameters:
        value_sequence: Sequence of approximations converging to limit
        target_order: Expected order of convergence
        
    Returns:
        Accelerated estimate of the limit
    """
    if len(value_sequence) < 3:
        return value_sequence[-1] if value_sequence else 0.0
    
    # Apply Aitken's delta-squared method
    s0 = value_sequence[-3]
    s1 = value_sequence[-2]
    s2 = value_sequence[-1]
    
    denom = s2 - 2 * s1 + s0
    if abs(denom) < 1e-15:
        return s2
    
    # Aitken's formula: s* = s0 - (s1 - s0)^2 / (s2 - 2*s1 + s0)
    accelerated = s0 - (s1 - s0) ** 2 / denom
    
    return accelerated


def estimate_extrapolation_error(estimates, extrapolated_value):
    """
    Estimate the error in the extrapolated value.
    
    Uses the difference between the last raw estimate and the
    extrapolated value as an error indicator.
    
    Parameters:
        estimates: Original sequence of estimates
        extrapolated_value: The Richardson-extrapolated result
        
    Returns:
        Estimated error bound
    """
    if not estimates:
        return float('inf')
    
    # The difference between raw and extrapolated gives error order
    last_raw = estimates[-1]
    error_indicator = abs(extrapolated_value - last_raw)
    
    # Also check consistency with second-to-last
    if len(estimates) >= 2:
        prev_raw = estimates[-2]
        prev_diff = abs(last_raw - prev_raw)
        if prev_diff > 0:
            # If extrapolation improved significantly, use smaller error
            improvement_ratio = error_indicator / prev_diff
            if improvement_ratio < 0.1:
                return error_indicator * 0.1
    
    return error_indicator
