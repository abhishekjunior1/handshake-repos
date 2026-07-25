"""
Adaptive ODE Solver Pipeline

Solves initial value problems (IVPs) using embedded Runge-Kutta methods
with adaptive step size control and stiffness detection:
1. Load problem specification (system of ODEs, initial conditions, parameters)
2. Configure solver (tolerances, method selection, step limits)
3. Integrate using RK45 with embedded error estimation
4. Apply adaptive step size control based on local error
5. Detect stiffness and switch to implicit method if needed
6. Generate structured output with solution trajectory and diagnostics

Usage: python3 /app/pipeline.py
Reads: /app/problem_spec.json
Writes: /app/output.json
"""

import json
import sys
import os

from problem_loader import load_problem, validate_problem_spec
from rk_methods import (
    rk45_step,
    rk4_step,
    implicit_euler_step,
    compute_embedded_error,
)
from step_controller import (
    compute_new_step_size,
    accept_step,
    StepSizeController,
)
from stiffness_detector import (
    detect_stiffness,
    StiffnessMonitor,
)
from interpolator import (
    hermite_interpolate,
    build_dense_output,
)
from report_generator import (
    build_solver_report,
    format_trajectory,
    compute_diagnostics,
)


def run_pipeline(input_path, output_path):
    """Execute the full ODE solver pipeline."""

    # Stage 1: Load and validate
    problem = load_problem(input_path)
    validation = validate_problem_spec(problem)
    if not validation["valid"]:
        sys.exit(f"Problem validation failed: {validation['errors']}")

    system = problem["system"]
    t_span = (system["t_start"], system["t_end"])
    y0 = system["initial_conditions"]
    params = system.get("parameters", {})
    solver_config = problem["solver_config"]

    # Stage 2: Configure solver
    atol = solver_config.get("atol", 1e-6)
    rtol = solver_config.get("rtol", 1e-3)
    max_step = solver_config.get("max_step", (t_span[1] - t_span[0]) / 10.0)
    min_step = solver_config.get("min_step", 1e-12)
    initial_step = solver_config.get("initial_step", (t_span[1] - t_span[0]) / 100.0)
    output_points = solver_config.get("output_points", 50)
    max_steps = solver_config.get("max_steps", 10000)

    # Build the RHS function from the problem specification
    rhs_func = _build_rhs_function(system["equations"], params)

    # Stage 3-5: Integrate
    controller = StepSizeController(
        atol=atol, rtol=rtol, max_step=max_step,
        min_step=min_step, safety_factor=0.9
    )
    stiffness_monitor = StiffnessMonitor(
        threshold=solver_config.get("stiffness_threshold", 3.0),
        window_size=solver_config.get("stiffness_window", 5),
    )

    t = t_span[0]
    y = y0[:]
    h = initial_step

    # Solution storage
    t_history = [t]
    y_history = [y[:]]
    step_count = 0
    rejected_steps = 0
    stiffness_switches = 0
    method_used = "rk45"

    while t < t_span[1] and step_count < max_steps:
        # Ensure we don't overshoot
        if t + h > t_span[1]:
            h = t_span[1] - t

        if h < min_step:
            h = min_step

        # Try a step with the current method
        if method_used == "rk45":
            y_new, y_err, k_stages = rk45_step(rhs_func, t, y, h)
            error_norm = compute_embedded_error(y, y_new, y_err, atol, rtol)
        else:
            # Implicit Euler for stiff systems
            y_new = implicit_euler_step(rhs_func, t, y, h)
            error_norm = 0.5  # Always accept implicit steps
            k_stages = None

        # Step size control
        if accept_step(error_norm):
            t = t + h
            y = y_new
            t_history.append(t)
            y_history.append(y[:])
            step_count += 1

            # Stiffness detection (only in RK mode)
            if method_used == "rk45" and k_stages is not None:
                is_stiff = stiffness_monitor.update(
                    rhs_func, t, y, h, k_stages
                )
                if is_stiff:
                    method_used = "implicit_euler"
                    stiffness_switches += 1
        else:
            rejected_steps += 1

        # Compute new step size
        h = compute_new_step_size(h, error_norm, controller)

    # Stage 6: Generate report
    # Build dense output at evenly spaced points
    t_output = _linspace(t_span[0], t_span[1], output_points)
    y_output = build_dense_output(t_history, y_history, t_output)

    trajectory = format_trajectory(t_output, y_output, system.get("variable_names", None))
    diagnostics = compute_diagnostics(
        step_count=step_count,
        rejected_steps=rejected_steps,
        stiffness_switches=stiffness_switches,
        final_time=t,
        method_used=method_used,
        h_final=h,
    )

    report = build_solver_report(
        problem_name=system["name"],
        trajectory=trajectory,
        diagnostics=diagnostics,
        solver_config=solver_config,
        t_span=t_span,
        n_equations=len(y0),
    )

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


def _build_rhs_function(equations, params):
    """
    Build a callable RHS function from the problem specification.

    The equations are specified as Python expressions that reference
    state variables y[0], y[1], ... and parameters by name.
    """
    def rhs(t, y):
        local_vars = {"t": t, "y": y, **params}
        import math
        local_vars["math"] = math
        local_vars["exp"] = math.exp
        local_vars["sin"] = math.sin
        local_vars["cos"] = math.cos
        local_vars["sqrt"] = math.sqrt
        local_vars["log"] = math.log
        local_vars["abs"] = abs

        dydt = []
        for eq in equations:
            dydt.append(float(eval(eq, {"__builtins__": {}}, local_vars)))
        return dydt

    return rhs


def _linspace(start, end, n):
    """Generate n evenly spaced points from start to end (inclusive)."""
    if n <= 1:
        return [start]
    step = (end - start) / (n - 1)
    return [start + i * step for i in range(n)]


if __name__ == "__main__":
    input_file = "/app/problem_spec.json"
    output_file = "/app/output.json"

    if not os.path.exists(input_file):
        sys.exit(f"Input file not found: {input_file}")

    report = run_pipeline(input_file, output_file)
    print(f"Integration complete. Results written to {output_file}")
    print(f"Problem: {report['problem_name']}")
    print(f"Steps: {report['diagnostics']['step_count']}, "
          f"Rejected: {report['diagnostics']['rejected_steps']}")
