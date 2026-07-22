"""
Base quadrature rules for numerical integration.
Implements composite Simpson's rule, Gauss-Kronrod pairs, and trapezoidal rule.
All rules operate on pre-computed function values at specified nodes.
"""

import math


def simpson_rule(f_values, h):
    """
    Apply composite Simpson's 1/3 rule to equally-spaced function values.
    
    Parameters:
        f_values: Function values at equally-spaced nodes (must be odd count >= 3)
        h: Spacing between nodes
        
    Returns:
        Approximate integral value
    """
    n = len(f_values)
    if n < 3 or n % 2 == 0:
        raise ValueError(f"Simpson's rule requires odd number of points >= 3, got {n}")
    
    result = f_values[0] + f_values[-1]
    
    for i in range(1, n - 1):
        if i % 2 == 0:
            result += 2.0 * f_values[i]
        else:
            result += 4.0 * f_values[i]
    
    return result * h / 3.0


def trapezoidal_rule(f_values, h):
    """
    Apply composite trapezoidal rule to equally-spaced function values.
    
    Parameters:
        f_values: Function values at equally-spaced nodes (must be >= 2)
        h: Spacing between nodes
        
    Returns:
        Approximate integral value
    """
    n = len(f_values)
    if n < 2:
        raise ValueError(f"Trapezoidal rule requires at least 2 points, got {n}")
    
    result = 0.5 * (f_values[0] + f_values[-1])
    for i in range(1, n - 1):
        result += f_values[i]
    
    return result * h


def gauss_kronrod_7_15(func_spec, a, b, evaluate_func):
    """
    Apply the Gauss-Kronrod G7/K15 rule pair on interval [a, b].
    
    Uses 7-point Gauss and 15-point Kronrod rules for integration
    with embedded error estimation.
    
    Parameters:
        func_spec: Function specification dict
        a, b: Integration interval endpoints
        evaluate_func: Function evaluator callable
        
    Returns:
        (gauss_result, kronrod_result) pair
    """
    # Gauss-Legendre 7-point nodes and weights on [-1, 1]
    gauss_nodes = [
        -0.9491079123427585,
        -0.7415311855993945,
        -0.4058451513773972,
        0.0,
        0.4058451513773972,
        0.7415311855993945,
        0.9491079123427585
    ]
    gauss_weights = [
        0.1294849661688697,
        0.2797053914892766,
        0.3818300505051189,
        0.4179591836734694,
        0.3818300505051189,
        0.2797053914892766,
        0.1294849661688697
    ]
    
    # Kronrod 15-point nodes and weights on [-1, 1]
    kronrod_nodes = [
        -0.9914553711208126,
        -0.9491079123427585,
        -0.8648644233597691,
        -0.7415311855993945,
        -0.5860872354676911,
        -0.4058451513773972,
        -0.2077849550078985,
        0.0,
        0.2077849550078985,
        0.4058451513773972,
        0.5860872354676911,
        0.7415311855993945,
        0.8648644233597691,
        0.9491079123427585,
        0.9914553711208126
    ]
    kronrod_weights = [
        0.0229353220105292,
        0.0630920926299786,
        0.1047900103222502,
        0.1406532597155259,
        0.1690047266392679,
        0.1903505780647854,
        0.2044329400752989,
        0.2094821410847278,
        0.2044329400752989,
        0.1903505780647854,
        0.1690047266392679,
        0.1406532597155259,
        0.1047900103222502,
        0.0630920926299786,
        0.0229353220105292
    ]
    
    # Transform from [-1, 1] to [a, b]
    mid = (a + b) / 2.0
    half_width = (b - a) / 2.0
    
    # Compute Gauss integral
    gauss_result = 0.0
    for i in range(7):
        x = mid + half_width * gauss_nodes[i]
        gauss_result += gauss_weights[i] * evaluate_func(func_spec, x)
    gauss_result *= half_width
    
    # Compute Kronrod integral
    kronrod_result = 0.0
    for i in range(15):
        x = mid + half_width * kronrod_nodes[i]
        kronrod_result += kronrod_weights[i] * evaluate_func(func_spec, x)
    kronrod_result *= half_width
    
    return gauss_result, kronrod_result


def adaptive_simpson_step(func_spec, a, b, evaluate_func, n_points=5):
    """
    Single step of adaptive Simpson's rule with n_points nodes.
    
    Parameters:
        func_spec: Function specification
        a, b: Interval endpoints
        evaluate_func: Function evaluator
        n_points: Number of quadrature nodes (must be odd >= 5)
        
    Returns:
        (coarse_estimate, fine_estimate, nodes, values)
        coarse uses n_points//2+1 nodes, fine uses all n_points
    """
    if n_points < 5 or n_points % 2 == 0:
        n_points = 5
    
    h = (b - a) / (n_points - 1)
    nodes = [a + i * h for i in range(n_points)]
    values = [evaluate_func(func_spec, x) for x in nodes]
    
    # Fine estimate using all points
    fine = simpson_rule(values, h)
    
    # Coarse estimate using every other point
    coarse_n = (n_points + 1) // 2
    if coarse_n % 2 == 0:
        coarse_n -= 1
    coarse_values = values[::2][:coarse_n]
    coarse_h = 2.0 * h
    coarse = simpson_rule(coarse_values, coarse_h)
    
    return coarse, fine, nodes, values


def compute_quadrature_with_refinement(func_spec, a, b, evaluate_func, 
                                        initial_points=5, max_refinements=4):
    """
    Compute integral with successive refinements for convergence assessment.
    
    Returns list of (n_points, integral_estimate) pairs for increasing resolution.
    Used by Richardson extrapolation to accelerate convergence.
    """
    results = []
    n_points = initial_points
    
    for _ in range(max_refinements):
        h = (b - a) / (n_points - 1)
        nodes = [a + i * h for i in range(n_points)]
        values = [evaluate_func(func_spec, x) for x in nodes]
        
        estimate = simpson_rule(values, h)
        results.append((n_points, h, estimate))
        
        # Double the points (keeping odd count)
        n_points = 2 * (n_points - 1) + 1
    
    return results


def midpoint_rule(func_spec, a, b, evaluate_func, n_panels):
    """
    Composite midpoint rule for integration.
    
    Parameters:
        func_spec: Function specification
        a, b: Interval endpoints
        evaluate_func: Function evaluator
        n_panels: Number of subintervals
        
    Returns:
        Approximate integral value
    """
    h = (b - a) / n_panels
    result = 0.0
    
    for i in range(n_panels):
        x_mid = a + (i + 0.5) * h
        result += evaluate_func(func_spec, x_mid)
    
    return result * h
