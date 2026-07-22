"""
Problem Loader Module

Loads and validates linear system problem specifications from JSON format.
Supports symmetric positive-definite systems defined in COO (coordinate)
sparse format with solver configuration parameters.

Expected JSON schema:
{
  "dimension": int,
  "matrix": {"rows": [...], "cols": [...], "values": [...]},
  "rhs": [...],
  "solver_params": {"max_iterations": int, "tolerance": float, "preconditioner": str}
}
"""

import math


def load_problem(config):
    """
    Parse a validated problem configuration into components.

    Parameters
    ----------
    config : dict
        Validated JSON configuration with matrix, rhs, dimension, solver_params.

    Returns
    -------
    dict
        Parsed problem with keys: A_data, b, n, solver_params.
    """
    return {
        "A_data": config["matrix"],
        "b": config["rhs"],
        "n": config["dimension"],
        "solver_params": config["solver_params"],
    }


def validate_problem(config):
    """
    Validate the problem specification for structural correctness.

    Checks:
    - Required top-level keys exist
    - Dimension is positive integer
    - Matrix COO format has consistent lengths
    - RHS vector matches dimension
    - Solver parameters are within valid ranges
    - Matrix indices are within bounds
    - Diagonal entries exist (required for Jacobi preconditioner)

    Parameters
    ----------
    config : dict
        Raw JSON configuration to validate.

    Returns
    -------
    dict
        {"valid": bool, "errors": list[str]}
    """
    errors = []

    # Check required keys
    required_keys = ["dimension", "matrix", "rhs", "solver_params"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required key: {key}")

    if errors:
        return {"valid": False, "errors": errors}

    # Validate dimension
    n = config["dimension"]
    if not isinstance(n, int) or n <= 0:
        errors.append(f"Dimension must be positive integer, got {n}")
        return {"valid": False, "errors": errors}

    # Validate matrix structure
    matrix = config["matrix"]
    matrix_keys = ["rows", "cols", "values"]
    for key in matrix_keys:
        if key not in matrix:
            errors.append(f"Matrix missing key: {key}")

    if errors:
        return {"valid": False, "errors": errors}

    rows = matrix["rows"]
    cols = matrix["cols"]
    values = matrix["values"]

    # Check consistent lengths
    if not (len(rows) == len(cols) == len(values)):
        errors.append(
            f"Matrix COO arrays have inconsistent lengths: "
            f"rows={len(rows)}, cols={len(cols)}, values={len(values)}"
        )

    # Check index bounds
    for i, (r, c) in enumerate(zip(rows, cols)):
        if r < 0 or r >= n:
            errors.append(f"Row index {r} out of bounds at position {i}")
            break
        if c < 0 or c >= n:
            errors.append(f"Col index {c} out of bounds at position {i}")
            break

    # Check for diagonal coverage (needed for Jacobi)
    diagonal_indices = set()
    for r, c in zip(rows, cols):
        if r == c:
            diagonal_indices.add(r)

    if len(diagonal_indices) < n:
        missing = set(range(n)) - diagonal_indices
        errors.append(
            f"Missing diagonal entries at indices: {sorted(missing)[:5]}..."
            if len(missing) > 5
            else f"Missing diagonal entries at indices: {sorted(missing)}"
        )

    # Validate RHS
    rhs = config["rhs"]
    if len(rhs) != n:
        errors.append(f"RHS length {len(rhs)} does not match dimension {n}")

    # Validate solver params
    params = config["solver_params"]
    if "max_iterations" not in params:
        errors.append("solver_params missing max_iterations")
    elif not isinstance(params["max_iterations"], int) or params["max_iterations"] <= 0:
        errors.append("max_iterations must be positive integer")

    if "tolerance" not in params:
        errors.append("solver_params missing tolerance")
    elif not isinstance(params["tolerance"], (int, float)) or params["tolerance"] <= 0:
        errors.append("tolerance must be positive number")
    elif params["tolerance"] >= 1.0:
        errors.append("tolerance must be less than 1.0")

    # Check for non-zero diagonal values
    for r, c, v in zip(rows, cols, values):
        if r == c and abs(v) < 1e-15:
            errors.append(f"Near-zero diagonal at ({r},{r}): {v}")
            break

    # Validate symmetry (spot check for COO format)
    entry_map = {}
    for r, c, v in zip(rows, cols, values):
        entry_map[(r, c)] = v

    symmetry_violations = 0
    for (r, c), v in entry_map.items():
        if r != c:
            transpose_val = entry_map.get((c, r))
            if transpose_val is None:
                symmetry_violations += 1
            elif abs(v - transpose_val) > 1e-12:
                symmetry_violations += 1

    if symmetry_violations > 0:
        errors.append(
            f"Matrix symmetry violations detected: {symmetry_violations} entries"
        )

    return {"valid": len(errors) == 0, "errors": errors}


def get_problem_summary(config):
    """
    Generate a human-readable summary of the problem specification.

    Parameters
    ----------
    config : dict
        Validated problem configuration.

    Returns
    -------
    str
        Multi-line summary string.
    """
    n = config["dimension"]
    nnz = len(config["matrix"]["values"])
    density = nnz / (n * n) * 100
    params = config["solver_params"]

    rhs = config["rhs"]
    rhs_norm = math.sqrt(sum(x * x for x in rhs))

    lines = [
        f"Problem Summary:",
        f"  Dimension: {n}x{n}",
        f"  Non-zeros: {nnz} ({density:.1f}% density)",
        f"  RHS norm: {rhs_norm:.6e}",
        f"  Max iterations: {params['max_iterations']}",
        f"  Tolerance: {params['tolerance']:.2e}",
        f"  Preconditioner: {params.get('preconditioner', 'jacobi')}",
    ]
    return "\n".join(lines)
