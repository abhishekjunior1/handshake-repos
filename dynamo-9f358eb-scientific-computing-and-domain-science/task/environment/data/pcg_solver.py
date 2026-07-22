"""
PCG Solver Module

Implements helper functions for the Preconditioned Conjugate Gradient method.
The main iteration loop is in pipeline.py; this module provides the
mathematical building blocks.

The PCG method solves Ax = b by iterating:
1. Compute step size alpha = (r^T z) / (p^T A p)
2. Update solution: x = x + alpha * p
3. Update residual: r = r - alpha * A*p
4. Apply preconditioner: z = M^{-1} r
5. Compute direction update: beta = (r_new^T z_new) / (r_old^T z_old)
6. Update search direction: p = z + beta * p

Convergence is guaranteed for SPD systems with any SPD preconditioner.
"""

import math


def pcg_iterate(A, M, x, r, p, rz_old, matrix_vector_fn, preconditioner_fn):
    """
    Perform a single PCG iteration step.

    Computes the full update cycle: step size, solution update,
    residual update, preconditioning, and direction update.

    Parameters
    ----------
    A : dict
        System matrix in CSR format.
    M : dict
        Preconditioner data structure.
    x : list[float]
        Current solution estimate.
    r : list[float]
        Current residual vector.
    p : list[float]
        Current search direction.
    rz_old : float
        Previous r^T z product.
    matrix_vector_fn : callable
        Function to compute A*p.
    preconditioner_fn : callable
        Function to compute M^{-1}*r.

    Returns
    -------
    dict
        Updated state with keys:
        - x: new solution
        - r: new residual
        - p: new search direction
        - rz_new: new r^T z product
        - residual_norm: ||r_new||_2
        - alpha: step size used
        - beta: direction mixing coefficient
        - breakdown: bool, True if p^T A p ≈ 0
    """
    n = len(x)

    # Compute A*p for step size and residual update
    Ap = matrix_vector_fn(A, p)

    # Step size: alpha = (r^T z) / (p^T A p)
    pAp = _dot(p, Ap)
    if abs(pAp) < 1e-15:
        return {
            "x": x, "r": r, "p": p,
            "rz_new": rz_old,
            "residual_norm": math.sqrt(_dot(r, r)),
            "alpha": 0.0, "beta": 0.0,
            "breakdown": True,
        }

    alpha = rz_old / pAp

    # Update solution: x_new = x + alpha * p
    x_new = [x[i] + alpha * p[i] for i in range(n)]

    # Update residual: r_new = r - alpha * A*p
    r_new = [r[i] - alpha * Ap[i] for i in range(n)]

    residual_norm = math.sqrt(_dot(r_new, r_new))

    # Apply preconditioner to new residual
    z_new = preconditioner_fn(M, r_new)

    # New rz product for beta computation
    rz_new = _dot(r_new, z_new)

    # Direction update coefficient
    beta = rz_new / rz_old if abs(rz_old) > 1e-15 else 0.0

    # New search direction: p_new = z_new + beta * p_old
    p_new = compute_search_direction(z_new, p, beta)

    return {
        "x": x_new,
        "r": r_new,
        "p": p_new,
        "rz_new": rz_new,
        "residual_norm": residual_norm,
        "alpha": alpha,
        "beta": beta,
        "breakdown": False,
    }


def compute_search_direction(z, p_old, beta):
    """
    Compute the new conjugate search direction.

    The search direction combines the preconditioned residual (steepest
    descent direction in the preconditioned space) with the previous
    search direction scaled by beta to maintain A-conjugacy.

    p_new = z + beta * p_old

    This ensures that consecutive search directions are A-conjugate:
    p_i^T A p_j = 0 for i ≠ j, which guarantees monotonic error
    reduction in the A-norm.

    Parameters
    ----------
    z : list[float]
        Preconditioned residual (M^{-1} * r).
    p_old : list[float]
        Previous search direction.
    beta : float
        Direction mixing coefficient (r_new^T z_new) / (r_old^T z_old).

    Returns
    -------
    list[float]
        New search direction p = z + beta * p_old.
    """
    n = len(z)
    p_new = [z[i] + beta * p_old[i] for i in range(n)]
    return p_new


def compute_step_size(r, z, p, Ap):
    """
    Compute the optimal step size along the search direction.

    alpha = (r^T z) / (p^T A p)

    This minimizes the A-norm of the error along direction p.

    Parameters
    ----------
    r : list[float]
        Current residual.
    z : list[float]
        Preconditioned residual.
    p : list[float]
        Current search direction.
    Ap : list[float]
        Matrix-vector product A*p.

    Returns
    -------
    float
        Optimal step size, or 0.0 if denominator is near zero.
    """
    rz = _dot(r, z)
    pAp = _dot(p, Ap)

    if abs(pAp) < 1e-15:
        return 0.0

    return rz / pAp


def compute_beta(rz_new, rz_old):
    """
    Compute the Fletcher-Reeves direction update coefficient.

    beta = (r_new^T z_new) / (r_old^T z_old)

    This coefficient determines how much of the previous search direction
    to retain in the update, ensuring A-conjugacy of successive directions.

    Parameters
    ----------
    rz_new : float
        New r^T z product (after residual update).
    rz_old : float
        Previous r^T z product.

    Returns
    -------
    float
        Beta coefficient, or 0.0 if rz_old is near zero.
    """
    if abs(rz_old) < 1e-15:
        return 0.0
    return rz_new / rz_old


def _dot(a, b):
    """Compute dot product of two vectors."""
    return sum(ai * bi for ai, bi in zip(a, b))


def verify_conjugacy(p_vectors, A, matrix_vector_fn, tol=1e-8):
    """
    Verify A-conjugacy of a set of search directions.

    For exact arithmetic, p_i^T A p_j should be zero for i ≠ j.
    In floating point, we check that the ratio to the diagonal
    products is below tolerance.

    Parameters
    ----------
    p_vectors : list[list[float]]
        Collection of search direction vectors.
    A : dict
        System matrix.
    matrix_vector_fn : callable
        Matrix-vector product function.
    tol : float
        Tolerance for conjugacy check.

    Returns
    -------
    dict
        Results with max_violation and is_conjugate flag.
    """
    k = len(p_vectors)
    max_violation = 0.0

    for i in range(k):
        Api = matrix_vector_fn(A, p_vectors[i])
        diag_i = _dot(p_vectors[i], Api)

        for j in range(i + 1, k):
            off_diag = _dot(p_vectors[j], Api)
            if abs(diag_i) > 1e-15:
                violation = abs(off_diag) / abs(diag_i)
                max_violation = max(max_violation, violation)

    return {
        "max_violation": max_violation,
        "is_conjugate": max_violation < tol,
    }
