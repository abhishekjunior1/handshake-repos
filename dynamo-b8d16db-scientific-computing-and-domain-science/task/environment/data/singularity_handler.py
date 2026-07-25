"""
Singularity handling module for adaptive quadrature.
Implements endpoint transformations for integrands with algebraic singularities,
using power-law variable substitution to regularize the integrand.
"""

import math
from utils import evaluate_function


def handle_singularity(func_spec, a, b, singularity_info, evaluate_func, n_points=15):
    """
    Apply singularity-handling transformation and integrate the regularized function.
    
    For an integrand with algebraic singularity f(x) ~ C * (x-a)^(-alpha) near x=a,
    applies the power-law substitution x = a + t^(1/(1-alpha)) to regularize the
    integrand, converting the singular behavior into a smooth function in t-space.
    
    This is a specialized alternative to the general tanh-sinh transformation,
    optimized for algebraic (power-law) singularities where the singularity
    exponent alpha is known or estimated.
    
    Parameters:
        func_spec: Function specification
        a, b: Integration interval
        singularity_info: Dict with 'endpoint', 'strength', 'location'
        evaluate_func: Function evaluator
        n_points: Number of quadrature nodes in transformed space
        
    Returns:
        (integral_estimate, transformation_quality)
    """
    alpha = singularity_info["strength"]
    endpoint = singularity_info["endpoint"]
    
    if alpha >= 1.0:
        # Non-integrable singularity — use truncation
        return _truncated_integration(func_spec, a, b, singularity_info, evaluate_func, n_points)
    
    if endpoint == "left":
        return _left_endpoint_transform(func_spec, a, b, alpha, evaluate_func, n_points)
    else:
        return _right_endpoint_transform(func_spec, a, b, alpha, evaluate_func, n_points)


def _left_endpoint_transform(func_spec, a, b, alpha, evaluate_func, n_points):
    """
    Handle left-endpoint singularity via power-law substitution.
    
    For f(x) with singularity at x=a of strength alpha:
    Substitution: x = a + (b-a) * t^gamma  where gamma = 1/(1-alpha)
    
    This maps t in [0,1] to x in [a,b], with:
    - dx = gamma * (b-a) * t^(gamma-1) dt
    - The Jacobian t^(gamma-1) cancels the singularity (x-a)^(-alpha)
    
    The transformed integrand g(t) = f(a + (b-a)*t^gamma) * gamma*(b-a)*t^(gamma-1)
    is smooth on [0,1] when gamma is chosen correctly for the singularity strength.
    
    This approach is standard in computational mathematics for handling endpoint
    algebraic singularities (see Davis & Rabinowitz, "Methods of Numerical Integration",
    Ch. 4.8; also Sag & Szekeres, 1964).
    """
    gamma = 1.0 / (1.0 - alpha)
    interval_width = b - a
    
    # Integrate g(t) on [0, 1] using Gauss-Legendre quadrature
    # Transform [0,1] to Gauss nodes on [-1,1]
    gauss_nodes, gauss_weights = _gauss_legendre_nodes(n_points)
    
    integral = 0.0
    max_jacobian = 0.0
    
    for i in range(n_points):
        # Map from [-1,1] to [0,1]
        t = 0.5 * (gauss_nodes[i] + 1.0)
        w = 0.5 * gauss_weights[i]
        
        if t < 1e-15:
            continue  # Skip t=0 to avoid 0^(gamma-1) issues
        
        # Power-law transformation: x = a + (b-a) * t^gamma
        x = a + interval_width * (t ** gamma)
        
        # Jacobian: dx/dt = gamma * (b-a) * t^(gamma-1)
        jacobian = gamma * interval_width * (t ** (gamma - 1.0))
        max_jacobian = max(max_jacobian, abs(jacobian))
        
        # Evaluate transformed integrand
        try:
            f_val = evaluate_func(func_spec, x)
            if math.isfinite(f_val):
                integral += w * f_val * jacobian
        except (ValueError, OverflowError):
            continue
    
    # Quality metric: ratio of max to min Jacobian (lower is better regularization)
    quality = 1.0 / (1.0 + math.log1p(max_jacobian)) if max_jacobian > 0 else 0.0
    
    return integral, quality


def _right_endpoint_transform(func_spec, a, b, alpha, evaluate_func, n_points):
    """
    Handle right-endpoint singularity via power-law substitution.
    
    Mirrors the left-endpoint transformation:
    Substitution: x = b - (b-a) * t^gamma  where gamma = 1/(1-alpha)
    """
    gamma = 1.0 / (1.0 - alpha)
    interval_width = b - a
    
    gauss_nodes, gauss_weights = _gauss_legendre_nodes(n_points)
    
    integral = 0.0
    max_jacobian = 0.0
    
    for i in range(n_points):
        t = 0.5 * (gauss_nodes[i] + 1.0)
        w = 0.5 * gauss_weights[i]
        
        if t < 1e-15:
            continue
        
        # Right-endpoint: x = b - (b-a) * t^gamma
        x = b - interval_width * (t ** gamma)
        
        # Jacobian: |dx/dt| = gamma * (b-a) * t^(gamma-1)
        jacobian = gamma * interval_width * (t ** (gamma - 1.0))
        max_jacobian = max(max_jacobian, abs(jacobian))
        
        try:
            f_val = evaluate_func(func_spec, x)
            if math.isfinite(f_val):
                integral += w * f_val * jacobian
        except (ValueError, OverflowError):
            continue
    
    quality = 1.0 / (1.0 + math.log1p(max_jacobian)) if max_jacobian > 0 else 0.0
    
    return integral, quality


def _truncated_integration(func_spec, a, b, singularity_info, evaluate_func, n_points):
    """
    For non-integrable singularities (alpha >= 1), truncate near the endpoint.
    Uses an epsilon-band exclusion with extrapolation.
    """
    endpoint = singularity_info["endpoint"]
    width = b - a
    epsilon = width * 1e-6
    
    if endpoint == "left":
        a_new = a + epsilon
        return _direct_quadrature(func_spec, a_new, b, evaluate_func, n_points), 0.1
    else:
        b_new = b - epsilon
        return _direct_quadrature(func_spec, a, b_new, evaluate_func, n_points), 0.1


def _direct_quadrature(func_spec, a, b, evaluate_func, n_points):
    """Simple Gauss-Legendre quadrature without transformation."""
    gauss_nodes, gauss_weights = _gauss_legendre_nodes(n_points)
    
    mid = (a + b) / 2.0
    half_width = (b - a) / 2.0
    
    integral = 0.0
    for i in range(n_points):
        x = mid + half_width * gauss_nodes[i]
        integral += gauss_weights[i] * evaluate_func(func_spec, x)
    
    return integral * half_width


def _gauss_legendre_nodes(n):
    """
    Return Gauss-Legendre nodes and weights for common point counts.
    Pre-computed for efficiency.
    """
    if n == 5:
        nodes = [
            -0.9061798459386640,
            -0.5384693101056831,
            0.0,
            0.5384693101056831,
            0.9061798459386640
        ]
        weights = [
            0.2369268850561891,
            0.4786286704993665,
            0.5688888888888889,
            0.4786286704993665,
            0.2369268850561891
        ]
    elif n == 10:
        nodes = [
            -0.9739065285171717, -0.8650633666889845, -0.6794095682990244,
            -0.4333953941292472, -0.1488743389816312,
            0.1488743389816312, 0.4333953941292472, 0.6794095682990244,
            0.8650633666889845, 0.9739065285171717
        ]
        weights = [
            0.0666713443086881, 0.1494513491505806, 0.2190863625159820,
            0.2692667193099963, 0.2955242247147529,
            0.2955242247147529, 0.2692667193099963, 0.2190863625159820,
            0.1494513491505806, 0.0666713443086881
        ]
    elif n == 15:
        nodes = [
            -0.9879925180204854, -0.9372733924007060, -0.8482065834104272,
            -0.7244177313601700, -0.5709721726085388, -0.3941513470775634,
            -0.2011940939974345, 0.0,
            0.2011940939974345, 0.3941513470775634, 0.5709721726085388,
            0.7244177313601700, 0.8482065834104272, 0.9372733924007060,
            0.9879925180204854
        ]
        weights = [
            0.0307532419961173, 0.0703660474881081, 0.1071592204671719,
            0.1395706779261543, 0.1662692058169939, 0.1861610000155622,
            0.1984314853271116, 0.2025782419255613,
            0.1984314853271116, 0.1861610000155622, 0.1662692058169939,
            0.1395706779261543, 0.1071592204671719, 0.0703660474881081,
            0.0307532419961173
        ]
    else:
        # Fallback: compute nodes using Newton's method for Legendre polynomials
        nodes = []
        weights = []
        for i in range(n):
            # Initial guess using Chebyshev node approximation
            x = math.cos(math.pi * (i + 0.75) / (n + 0.5))
            
            for _ in range(100):
                p0, p1 = 1.0, x
                for j in range(2, n + 1):
                    p0, p1 = p1, ((2*j - 1) * x * p1 - (j - 1) * p0) / j
                
                dp = n * (x * p1 - p0) / (x * x - 1.0) if abs(x * x - 1.0) > 1e-15 else 0.0
                if abs(dp) < 1e-15:
                    break
                x -= p1 / dp
            
            nodes.append(x)
            dp_final = n * (x * p1 - p0) / (x * x - 1.0) if abs(x*x - 1.0) > 1e-15 else n*n
            weights.append(2.0 / ((1.0 - x*x) * dp_final * dp_final) if abs(dp_final) > 1e-15 else 0.0)
        
        nodes.sort()
        weights = [w for _, w in sorted(zip([abs(n) for n in nodes], weights))]
    
    return nodes, weights


def assess_singularity_strength(func_spec, a, b, evaluate_func, endpoint="left"):
    """
    Assess the algebraic singularity strength at an endpoint.
    
    Estimates alpha in f(x) ~ C*(x-c)^(-alpha) by evaluating the
    function at geometrically decreasing distances from the endpoint.
    
    Parameters:
        func_spec: Function specification
        a, b: Interval endpoints
        evaluate_func: Function evaluator
        endpoint: Which endpoint to assess ("left" or "right")
        
    Returns:
        Estimated singularity strength alpha (0 = no singularity)
    """
    width = b - a
    
    if endpoint == "left":
        base = a
        direction = 1.0
    else:
        base = b
        direction = -1.0
    
    # Sample at geometrically decreasing distances
    distances = [width * 0.1 * (0.5 ** k) for k in range(6)]
    log_dist = []
    log_val = []
    
    for d in distances:
        x = base + direction * d
        if a <= x <= b:
            try:
                val = evaluate_func(func_spec, x)
                if val > 0 and math.isfinite(val):
                    log_dist.append(math.log(d))
                    log_val.append(math.log(val))
            except (ValueError, OverflowError):
                pass
    
    if len(log_dist) < 3:
        return 0.0
    
    # Linear regression of log(f) vs log(distance) to estimate -alpha
    n = len(log_dist)
    sum_x = sum(log_dist)
    sum_y = sum(log_val)
    sum_xy = sum(x * y for x, y in zip(log_dist, log_val))
    sum_xx = sum(x * x for x in log_dist)
    
    denom = n * sum_xx - sum_x * sum_x
    if abs(denom) < 1e-15:
        return 0.0
    
    slope = (n * sum_xy - sum_x * sum_y) / denom
    
    # slope = -alpha for f(x) ~ C*(x-c)^(-alpha)
    alpha = -slope
    
    return max(alpha, 0.0)
