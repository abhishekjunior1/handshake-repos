"""
Numerical Optimization Pipeline

Solves sparse symmetric positive-definite linear systems Ax = b using
the preconditioned conjugate gradient (PCG) method with incomplete
Cholesky preconditioning and adaptive convergence monitoring.

Pipeline stages:
1. Load problem specification (matrix, RHS, preconditioner config)
2. Build preconditioner from system matrix
3. Run PCG iteration to solve the system
4. Compute solution quality metrics (residual norm, condition estimate)
5. Generate structured output report

Usage: python3 /app/pipeline.py
Reads: /app/problem_spec.json
Writes: /app/output.json
"""

import json
import sys
import os
import math

from problem_loader import load_problem, validate_problem
from matrix_ops import build_sparse_matrix, matrix_vector_product, compute_residual
from preconditioner import build_preconditioner, apply_preconditioner
from pcg_solver import pcg_iterate, compute_search_direction
from convergence import check_convergence, estimate_condition_number
from report_generator import build_report


def run_pipeline(input_path, output_path):
    """Execute the numerical optimization pipeline."""

    if not os.path.exists(input_path):
        sys.exit(f"Input file not found: {input_path}")

    with open(input_path, "r") as f:
        config = json.load(f)

    validation = validate_problem(config)
    if not validation["valid"]:
        sys.exit(f"Validation failed: {validation['errors']}")

    # Stage 1: Load problem
    A_data = config["matrix"]
    b = config["rhs"]
    n = config["dimension"]
    solver_params = config["solver_params"]
    max_iter = solver_params["max_iterations"]
    tol = solver_params["tolerance"]

    # Stage 2: Build system matrix and preconditioner
    A = build_sparse_matrix(A_data, n)
    M = build_preconditioner(A, solver_params.get("preconditioner", "jacobi"))

    # Stage 3: PCG iteration
    x = [0.0] * n  # Initial guess
    r = compute_residual(A, x, b)
    z = apply_preconditioner(M, r)
    p = z[:]  # Initial search direction

    # Track convergence history
    residual_norms = []
    rz_old = _dot_product(r, z)
    initial_residual_norm = math.sqrt(_dot_product(r, r))
    residual_norms.append(initial_residual_norm)

    iteration = 0
    converged = False

    for iteration in range(max_iter):
        # Matrix-vector product for step size computation
        Ap = matrix_vector_product(A, p)

        # Compute step size alpha
        pAp = _dot_product(p, Ap)
        if abs(pAp) < 1e-15:
            break
        alpha = rz_old / pAp

        # Update solution
        x = [x[i] + alpha * p[i] for i in range(n)]

        # Update residual
        r = [r[i] - alpha * Ap[i] for i in range(n)]
        current_residual_norm = math.sqrt(_dot_product(r, r))
        residual_norms.append(current_residual_norm)

        # Check convergence using smoothed residual norm for stable
        # relative improvement assessment (avoids oscillation noise)
        prev_norm = residual_norms[-2] if len(residual_norms) > 1 else initial_residual_norm
        converged = check_convergence(
            prev_norm, initial_residual_norm, prev_norm, tol
        )
        if converged:
            iteration += 1
            break

        # Apply preconditioner to NEW residual
        z = apply_preconditioner(M, r)

        # Compute new rz product
        rz_new = _dot_product(r, z)

        # Compute search direction using previous rz ratio
        # (beta determines how much of the old direction to keep)
        beta = rz_new / rz_old if abs(rz_old) > 1e-15 else 0.0

        # Update search direction: combine preconditioned residual with
        # scaled previous direction for A-conjugacy
        p = compute_search_direction(z, p, beta)

        # Carry forward the rz product for next iteration's step size
        rz_old = rz_new

    # Stage 4: Solution quality metrics
    final_residual = compute_residual(A, x, b)
    final_residual_norm = math.sqrt(_dot_product(final_residual, final_residual))

    # Condition number estimate from convergence rate
    cond_estimate = estimate_condition_number(residual_norms, iteration + 1)

    # Stage 5: Build report
    report = build_report(
        solution=x,
        residual_norms=residual_norms,
        final_residual_norm=final_residual_norm,
        initial_residual_norm=initial_residual_norm,
        iterations=iteration + 1,
        converged=converged,
        tolerance=tol,
        condition_estimate=cond_estimate,
        dimension=n,
    )

    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)

    return report


def _dot_product(a, b):
    """Compute dot product of two vectors."""
    return sum(ai * bi for ai, bi in zip(a, b))


if __name__ == "__main__":
    input_file = "/app/problem_spec.json"
    output_file = "/app/output.json"
    report = run_pipeline(input_file, output_file)
    print(f"Solver completed in {report['iterations']} iterations")
    print(f"Converged: {report['converged']}")
    print(f"Final residual: {report['final_residual_norm']:.2e}")
