"""
Report generator module for the ODE solver pipeline.

Formats the integration trajectory, solver diagnostics, and problem
metadata into a structured JSON report.
"""


def format_trajectory(t_output, y_output, variable_names=None):
    """
    Format the solution trajectory for the report.

    Parameters
    ----------
    t_output : list of float
        Output time points.
    y_output : list of list of float
        Solution values at output points.
    variable_names : list of str or None
        Names for state variables.

    Returns
    -------
    list of dict
        Trajectory entries with time and state values.
    """
    if variable_names is None:
        n = len(y_output[0]) if y_output else 0
        variable_names = [f"y{i}" for i in range(n)]

    trajectory = []
    for i, (t, y) in enumerate(zip(t_output, y_output)):
        entry = {"time": round(t, 10)}
        for j, name in enumerate(variable_names):
            entry[name] = round(y[j], 10)
        trajectory.append(entry)

    return trajectory


def compute_diagnostics(step_count, rejected_steps, stiffness_switches,
                        final_time, method_used, h_final):
    """
    Compute solver diagnostics for the report.

    Parameters
    ----------
    step_count : int
        Total accepted steps.
    rejected_steps : int
        Total rejected steps.
    stiffness_switches : int
        Number of times the solver switched methods.
    final_time : float
        Final integration time reached.
    method_used : str
        Final integration method.
    h_final : float
        Final step size.

    Returns
    -------
    dict
        Solver diagnostics.
    """
    total_attempts = step_count + rejected_steps
    acceptance_rate = step_count / total_attempts if total_attempts > 0 else 1.0

    return {
        "step_count": step_count,
        "rejected_steps": rejected_steps,
        "total_function_evaluations": step_count * 7 + rejected_steps * 7,
        "acceptance_rate": round(acceptance_rate, 6),
        "stiffness_switches": stiffness_switches,
        "final_method": method_used,
        "final_time": round(final_time, 10),
        "final_step_size": round(h_final, 10),
    }


def build_solver_report(problem_name, trajectory, diagnostics, solver_config,
                        t_span, n_equations):
    """
    Assemble the complete solver report.

    Parameters
    ----------
    problem_name : str
        Name of the ODE problem.
    trajectory : list of dict
        Formatted solution trajectory.
    diagnostics : dict
        Solver performance diagnostics.
    solver_config : dict
        Solver configuration used.
    t_span : tuple of float
        Integration time interval.
    n_equations : int
        Number of equations in the system.

    Returns
    -------
    dict
        Complete solver report.
    """
    # Extract final values
    final_state = {}
    if trajectory:
        last = trajectory[-1]
        for key, value in last.items():
            if key != "time":
                final_state[key] = value

    return {
        "problem_name": problem_name,
        "n_equations": n_equations,
        "t_span": list(t_span),
        "solver_config": {
            "atol": solver_config.get("atol"),
            "rtol": solver_config.get("rtol"),
            "max_step": solver_config.get("max_step"),
            "output_points": solver_config.get("output_points"),
        },
        "trajectory": trajectory,
        "final_state": final_state,
        "diagnostics": diagnostics,
    }
