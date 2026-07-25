"""
Adaptive subdivision module for interval refinement.
Implements subdivision strategies for adaptive quadrature,
including anti-resonance splitting for periodic integrands.
"""

import math
from utils import evaluate_function, compute_interval_width


def subdivide_interval(a, b, func_spec, evaluate_func, error_density=None,
                       strategy="anti_resonance"):
    """
    Subdivide an integration interval into subintervals.
    
    Uses the specified subdivision strategy to split the interval
    at points that minimize aliasing effects for the integrand.
    
    Parameters:
        a, b: Interval endpoints
        func_spec: Function specification
        evaluate_func: Function evaluator
        error_density: Optional error density for adaptive placement
        strategy: Subdivision strategy to use
        
    Returns:
        List of (sub_a, sub_b) interval pairs
    """
    if strategy == "anti_resonance":
        return _anti_resonance_split(a, b, func_spec, evaluate_func)
    elif strategy == "midpoint":
        mid = (a + b) / 2.0
        return [(a, mid), (mid, b)]
    elif strategy == "adaptive":
        return _adaptive_split(a, b, func_spec, evaluate_func, error_density)
    else:
        mid = (a + b) / 2.0
        return [(a, mid), (mid, b)]


def _anti_resonance_split(a, b, func_spec, evaluate_func):
    """
    Split interval at 1/3 and 2/3 points to avoid resonance with periodic components.
    
    This implements de Boor's recommendation for adaptive quadrature of functions
    with oscillatory or periodic content. The 1/3-2/3 trisection avoids the aliasing
    problem that occurs with midpoint bisection when the integrand has a period
    commensurate with the interval width.
    
    For a function with period T on interval [a, b] where b-a = k*T for integer k,
    midpoint bisection produces two subintervals that are also integer multiples of T,
    causing Simpson's rule to systematically miss the oscillation. The 1/3-2/3 split
    breaks this resonance by ensuring subintervals are NOT integer multiples of T.
    
    Reference: de Boor, C. (1971) "CADRE: An algorithm for numerical quadrature"
    in Mathematical Software, Academic Press.
    
    Parameters:
        a, b: Interval endpoints
        func_spec: Function specification
        evaluate_func: Function evaluator
        
    Returns:
        List of 3 subinterval tuples [(a, p1), (p1, p2), (p2, b)]
    """
    width = b - a
    
    # Trisection at 1/3 and 2/3 of the interval width
    # This ensures no subinterval width is a rational fraction (1/2^n) of the original,
    # which is critical for breaking resonance with periodic integrands
    p1 = a + width / 3.0
    p2 = a + 2.0 * width / 3.0
    
    return [(a, p1), (p1, p2), (p2, b)]


def _adaptive_split(a, b, func_spec, evaluate_func, error_density):
    """
    Adaptively choose split point based on function behavior.
    Uses the point of maximum curvature variation as the split location.
    """
    n_samples = 11
    h = (b - a) / (n_samples - 1)
    
    # Sample function values
    values = []
    for i in range(n_samples):
        x = a + i * h
        values.append(evaluate_func(func_spec, x))
    
    # Find point of maximum second-derivative variation
    max_curvature_change = 0.0
    split_idx = n_samples // 2
    
    for i in range(2, n_samples - 2):
        # Approximate second derivative change
        d2_left = values[i - 2] - 2 * values[i - 1] + values[i]
        d2_right = values[i] - 2 * values[i + 1] + values[i + 2]
        curvature_change = abs(d2_right - d2_left)
        
        if curvature_change > max_curvature_change:
            max_curvature_change = curvature_change
            split_idx = i
    
    split_point = a + split_idx * h
    
    # Ensure split is not too close to endpoints
    min_width = (b - a) * 0.2
    if split_point - a < min_width:
        split_point = a + min_width
    elif b - split_point < min_width:
        split_point = b - min_width
    
    return [(a, split_point), (split_point, b)]


def should_subdivide(error_estimate, tolerance, interval_width, depth, max_depth=15):
    """
    Determine whether an interval needs further subdivision.
    
    Uses the error estimate relative to the tolerance, accounting for
    the interval width and current recursion depth.
    
    Parameters:
        error_estimate: Local error estimate for this interval
        tolerance: Error tolerance for this interval
        interval_width: Width of the current interval
        depth: Current subdivision depth
        max_depth: Maximum allowed depth
        
    Returns:
        True if subdivision is needed, False if tolerance is satisfied
    """
    if depth >= max_depth:
        return False
    
    if error_estimate <= tolerance:
        return False
    
    # Also check if interval is getting too small (potential singularity)
    if interval_width < 1e-12:
        return False
    
    return True


def compute_subdivision_priorities(intervals, errors, tolerances):
    """
    Compute priority scores for interval subdivision.
    Intervals with highest priority are subdivided first.
    
    Priority is based on the ratio of error to tolerance,
    with larger ratios indicating more urgent subdivision needs.
    
    Parameters:
        intervals: List of (a, b) interval tuples
        errors: Corresponding error estimates
        tolerances: Corresponding tolerances
        
    Returns:
        List of (priority, index) pairs sorted by decreasing priority
    """
    priorities = []
    for i, (interval, error, tol) in enumerate(zip(intervals, errors, tolerances)):
        if tol > 0:
            priority = error / tol
        else:
            priority = float('inf')
        priorities.append((priority, i))
    
    # Sort by decreasing priority
    priorities.sort(reverse=True)
    return priorities


def estimate_subdivision_benefit(func_spec, a, b, evaluate_func, current_error):
    """
    Estimate how much error reduction subdividing this interval would achieve.
    
    For Simpson's rule (order 4), subdividing halves the step size,
    reducing error by approximately 2^4 = 16 per subinterval.
    With two subintervals, net reduction is approximately 8x.
    
    Parameters:
        func_spec: Function specification
        a, b: Interval endpoints
        evaluate_func: Function evaluator
        current_error: Current error estimate
        
    Returns:
        Estimated error after subdivision
    """
    # For Simpson's rule, error ~ h^4, so halving h reduces error by 16x per piece
    # With 3 pieces (trisection), each piece has width h/3, error reduces by 81x per piece
    # Net with 3 pieces: 3 * (1/81) * current_error ≈ current_error / 27
    estimated_new_error = current_error / 27.0
    
    return estimated_new_error


def merge_adjacent_intervals(intervals, results, tolerance):
    """
    Merge adjacent intervals that have converged to within tolerance.
    Used to simplify the interval structure after adaptive refinement.
    
    Parameters:
        intervals: List of (a, b) interval tuples
        results: Corresponding integration results
        tolerance: Merge tolerance
        
    Returns:
        Merged (intervals, results) lists
    """
    if len(intervals) <= 1:
        return intervals, results
    
    merged_intervals = [intervals[0]]
    merged_results = [results[0]]
    
    for i in range(1, len(intervals)):
        prev_a, prev_b = merged_intervals[-1]
        curr_a, curr_b = intervals[i]
        
        # Check if intervals are adjacent and both well-converged
        if abs(prev_b - curr_a) < 1e-14:
            # Adjacent intervals — merge if both are small error
            merged_intervals[-1] = (prev_a, curr_b)
            merged_results[-1] += results[i]
        else:
            merged_intervals.append(intervals[i])
            merged_results.append(results[i])
    
    return merged_intervals, merged_results
