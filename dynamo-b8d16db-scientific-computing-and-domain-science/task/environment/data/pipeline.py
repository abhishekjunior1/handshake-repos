"""
Adaptive Quadrature Integration Pipeline
=========================================
Orchestrates multi-level adaptive numerical integration using:
- Composite Simpson/Kronrod quadrature rules
- Paired-rule error estimation
- Richardson extrapolation for convergence acceleration
- Anti-resonance subdivision strategy
- Power-law singularity handling

Reads function specification and integration parameters from input.json,
produces integration results in output.json.
"""

import json
import math
import sys

from utils import (evaluate_function, compute_interval_width, load_input,
                   save_output, format_result, detect_singularity)
from quadrature import (simpson_rule, gauss_kronrod_7_15, adaptive_simpson_step,
                        compute_quadrature_with_refinement)
from error_estimator import (estimate_local_error, compute_global_error_estimate,
                             assess_error_decay_rate, validate_error_estimate)
from extrapolator import (richardson_extrapolate, estimate_extrapolation_error,
                          extrapolate_convergence)
from subdivider import (subdivide_interval, should_subdivide,
                        compute_subdivision_priorities)
from singularity_handler import (handle_singularity, assess_singularity_strength)


def run_adaptive_quadrature(config):
    """
    Main adaptive quadrature integration routine.
    
    Implements a multi-phase integration strategy:
    1. Initial coarse/fine quadrature on the full interval
    2. Error estimation and convergence assessment
    3. Richardson extrapolation for sequence acceleration
    4. Adaptive subdivision of intervals exceeding tolerance
    5. Singularity detection and specialized handling
    
    Parameters:
        config: Integration configuration dictionary
        
    Returns:
        Result dictionary with integral value, error estimate, and diagnostics
    """
    func_spec = config["function"]
    a = config["interval"]["lower"]
    b = config["interval"]["upper"]
    tolerance = config["tolerance"]
    max_subdivisions = config.get("max_subdivisions", 50)
    singularity_detection = config.get("singularity_detection", True)
    
    # Phase 1: Initial quadrature with refinement sequence
    refinement_results = compute_quadrature_with_refinement(
        func_spec, a, b, evaluate_function, 
        initial_points=5, max_refinements=4
    )
    
    # Phase 2: Richardson extrapolation on the refinement sequence
    estimates = [r[2] for r in refinement_results]
    step_sizes = [r[1] for r in refinement_results]
    
    extrapolated_value, convergence_order = richardson_extrapolate(
        estimates, step_sizes
    )
    
    extrapolation_error = estimate_extrapolation_error(estimates, extrapolated_value)
    
    # Phase 3: Check if initial extrapolation meets tolerance
    if validate_error_estimate(extrapolation_error, extrapolated_value, tolerance):
        # Converged on full interval — check for singularities
        singularity_strength = 0.0
        if singularity_detection:
            sing_info = detect_singularity(func_spec, a, b)
            if sing_info:
                singularity_strength = sing_info["strength"]
        
        return format_result(
            integral_value=extrapolated_value,
            error_estimate=extrapolation_error,
            subdivisions=0,
            convergence_order=convergence_order,
            singularity_strength=singularity_strength,
            method_info={"method": "richardson_extrapolation", "levels": len(estimates)}
        )
    
    # Phase 4: Adaptive subdivision required
    integral_value, error_estimate, subdivisions, singularity_strength = (
        _adaptive_subdivision_loop(
            func_spec, a, b, tolerance, max_subdivisions, singularity_detection
        )
    )
    
    # Phase 5: Final convergence order assessment from error decay
    error_sequence = [(r[1], abs(r[2] - extrapolated_value)) for r in refinement_results
                      if abs(r[2] - extrapolated_value) > 1e-16]
    final_convergence_order = assess_error_decay_rate(error_sequence)
    if final_convergence_order == 0.0:
        final_convergence_order = convergence_order
    
    return format_result(
        integral_value=integral_value,
        error_estimate=error_estimate,
        subdivisions=subdivisions,
        convergence_order=final_convergence_order,
        singularity_strength=singularity_strength,
        method_info={
            "method": "adaptive_quadrature",
            "subdivisions_used": subdivisions,
            "extrapolation_estimate": extrapolated_value
        }
    )


def _adaptive_subdivision_loop(func_spec, a, b, tolerance, max_subdivisions,
                                singularity_detection):
    """
    Perform adaptive subdivision until all intervals meet tolerance.
    
    Maintains a priority queue of intervals, subdividing those with
    the highest error density first.
    """
    # Initialize with the full interval
    intervals = [(a, b)]
    interval_results = []
    interval_errors = []
    total_subdivisions = 0
    singularity_strength = 0.0
    
    # Compute initial estimates for each interval
    for (ia, ib) in intervals:
        coarse, fine, nodes, values = adaptive_simpson_step(
            func_spec, ia, ib, evaluate_function, n_points=9
        )
        
        error = estimate_local_error(func_spec, ia, ib, coarse, fine)
        interval_results.append(fine)
        interval_errors.append(error)
    
    # Adaptive refinement loop
    while total_subdivisions < max_subdivisions:
        # Find interval with largest error exceeding tolerance
        worst_idx = -1
        worst_error = 0.0
        
        for i, (interval, error) in enumerate(zip(intervals, interval_errors)):
            width = compute_interval_width(interval[0], interval[1])
            # Use the global absolute tolerance for subdivision decisions.
            # This provides consistent precision control across all subintervals
            # regardless of their local contribution to the total integral.
            local_tolerance = tolerance
            
            if error > local_tolerance and error > worst_error:
                worst_error = error
                worst_idx = i
        
        if worst_idx == -1:
            break  # All intervals within tolerance
        
        # Subdivide the worst interval
        wa, wb = intervals[worst_idx]
        
        # Check for singularity before subdivision
        if singularity_detection:
            sing_info = detect_singularity(func_spec, wa, wb)
            if sing_info and sing_info["strength"] > 0.15:
                # Use singularity handler for this interval
                sing_result, quality = handle_singularity(
                    func_spec, wa, wb, sing_info, evaluate_function
                )
                singularity_strength = max(singularity_strength, sing_info["strength"])
                
                # Replace interval with singularity-handled result
                intervals[worst_idx] = (wa, wb)
                interval_results[worst_idx] = sing_result
                interval_errors[worst_idx] = abs(sing_result) * tolerance * 0.1
                total_subdivisions += 1
                continue
        
        # Apply anti-resonance subdivision
        sub_intervals = subdivide_interval(wa, wb, func_spec, evaluate_function)
        
        # Remove the subdivided interval and add new ones
        intervals.pop(worst_idx)
        interval_results.pop(worst_idx)
        interval_errors.pop(worst_idx)
        
        for (sa, sb) in sub_intervals:
            coarse, fine, nodes, values = adaptive_simpson_step(
                func_spec, sa, sb, evaluate_function, n_points=9
            )
            
            error = estimate_local_error(func_spec, sa, sb, coarse, fine)
            intervals.append((sa, sb))
            interval_results.append(fine)
            interval_errors.append(error)
        
        total_subdivisions += 1
    
    # Compute final integral as sum of interval contributions
    total_integral = sum(interval_results)
    
    # Compute global error estimate
    error_pairs = [(compute_interval_width(iv[0], iv[1]), err) 
                   for iv, err in zip(intervals, interval_errors)]
    global_error = compute_global_error_estimate(error_pairs)
    
    return total_integral, global_error, total_subdivisions, singularity_strength


def main():
    """Entry point: load input, run integration, save output."""
    input_path = "/app/input.json"
    output_path = "/app/output.json"
    
    config = load_input(input_path)
    result = run_adaptive_quadrature(config)
    save_output(result, output_path)
    
    print(f"Integration complete: {result['integral_value']:.12f}")
    print(f"Error estimate: {result['error_estimate']:.2e}")
    print(f"Subdivisions: {result['subdivisions']}")
    print(f"Convergence order: {result['convergence_order']:.4f}")


if __name__ == "__main__":
    main()
