"""
Report Generator Module

Formats the PCG solver results into a structured JSON report. Computes
derived quality metrics including relative residual, convergence efficiency,
and solution statistics.

The output schema is designed for downstream validation and comparison
with reference solutions.
"""

import math


def build_report(
    solution,
    residual_norms,
    final_residual_norm,
    initial_residual_norm,
    iterations,
    converged,
    tolerance,
    condition_estimate,
    dimension,
):
    """
    Build a structured report from PCG solver results.

    Assembles all solver outputs into a single dictionary suitable for
    JSON serialization. Computes derived metrics that characterize
    solution quality and solver performance.

    Parameters
    ----------
    solution : list[float]
        Computed solution vector x.
    residual_norms : list[float]
        Full history of residual norms (including initial).
    final_residual_norm : float
        ||b - Ax|| at termination.
    initial_residual_norm : float
        ||b - A*x_0|| at start.
    iterations : int
        Number of PCG iterations performed.
    converged : bool
        Whether convergence criterion was satisfied.
    tolerance : float
        Requested relative tolerance.
    condition_estimate : float
        Estimated spectral condition number.
    dimension : int
        System dimension n.

    Returns
    -------
    dict
        Structured report with solver results and quality metrics.
    """
    # Compute relative residual
    relative_residual = (
        final_residual_norm / initial_residual_norm
        if initial_residual_norm > 1e-15
        else 0.0
    )

    # Solution statistics
    sol_norm = math.sqrt(sum(x * x for x in solution))
    sol_max = max(abs(x) for x in solution) if solution else 0.0
    sol_min = min(abs(x) for x in solution) if solution else 0.0

    # Convergence efficiency: ratio of iterations to dimension
    # For well-conditioned systems, PCG converges in << n iterations
    efficiency = iterations / dimension if dimension > 0 else 0.0

    # Theoretical bound on iterations for this condition number
    # PCG converges in at most n iterations for an n×n system,
    # but typically in O(sqrt(kappa)) iterations
    if condition_estimate > 1.0:
        theoretical_bound = math.sqrt(condition_estimate)
    else:
        theoretical_bound = 1.0

    # Build convergence history summary
    convergence_history = _build_convergence_summary(residual_norms)

    report = {
        "status": "completed",
        "converged": converged,
        "iterations": iterations,
        "dimension": dimension,
        "tolerance_requested": tolerance,
        "solution": [round(x, 12) for x in solution],
        "residual_norms": [round(rn, 12) for rn in residual_norms],
        "final_residual_norm": round(final_residual_norm, 12),
        "initial_residual_norm": round(initial_residual_norm, 12),
        "relative_residual": round(relative_residual, 12),
        "condition_estimate": round(condition_estimate, 6),
        "solver_metrics": {
            "efficiency": round(efficiency, 6),
            "theoretical_iteration_bound": round(theoretical_bound, 2),
            "solution_norm": round(sol_norm, 12),
            "solution_max_component": round(sol_max, 12),
            "solution_min_component": round(sol_min, 12),
        },
        "convergence_history": convergence_history,
    }

    return report


def _build_convergence_summary(residual_norms):
    """
    Build a summary of convergence behavior from residual history.

    Includes reduction factor, monotonicity check, and rate statistics.

    Parameters
    ----------
    residual_norms : list[float]
        Full residual norm history.

    Returns
    -------
    dict
        Summary statistics of convergence behavior.
    """
    if len(residual_norms) < 2:
        return {
            "total_reduction": 1.0,
            "is_monotone": True,
            "max_ratio": 0.0,
            "min_ratio": 0.0,
            "ratios": [],
        }

    # Compute successive ratios
    ratios = []
    for i in range(1, len(residual_norms)):
        if residual_norms[i - 1] > 1e-300:
            ratios.append(residual_norms[i] / residual_norms[i - 1])
        else:
            ratios.append(0.0)

    # Total reduction factor
    total_reduction = (
        residual_norms[-1] / residual_norms[0]
        if residual_norms[0] > 1e-300
        else 0.0
    )

    # Monotonicity check
    is_monotone = all(r <= 1.0 + 1e-10 for r in ratios)

    return {
        "total_reduction": round(total_reduction, 12),
        "is_monotone": is_monotone,
        "max_ratio": round(max(ratios), 12) if ratios else 0.0,
        "min_ratio": round(min(ratios), 12) if ratios else 0.0,
        "ratios": [round(r, 12) for r in ratios],
    }


def format_solution_vector(solution, precision=6):
    """
    Format solution vector for display.

    Parameters
    ----------
    solution : list[float]
        Solution vector.
    precision : int
        Number of decimal places.

    Returns
    -------
    str
        Formatted string representation.
    """
    entries = [f"  x[{i}] = {v:.{precision}e}" for i, v in enumerate(solution)]
    return "\n".join(entries)


def validate_report(report):
    """
    Validate that a report has all required fields.

    Parameters
    ----------
    report : dict
        Report to validate.

    Returns
    -------
    dict
        {"valid": bool, "missing_fields": list[str]}
    """
    required_fields = [
        "status",
        "converged",
        "iterations",
        "dimension",
        "tolerance_requested",
        "solution",
        "residual_norms",
        "final_residual_norm",
        "initial_residual_norm",
        "relative_residual",
        "condition_estimate",
        "solver_metrics",
        "convergence_history",
    ]

    missing = [f for f in required_fields if f not in report]

    if not missing and "solver_metrics" in report:
        metrics_fields = [
            "efficiency",
            "theoretical_iteration_bound",
            "solution_norm",
            "solution_max_component",
            "solution_min_component",
        ]
        missing_metrics = [f for f in metrics_fields if f not in report["solver_metrics"]]
        missing.extend(f"solver_metrics.{f}" for f in missing_metrics)

    return {"valid": len(missing) == 0, "missing_fields": missing}
