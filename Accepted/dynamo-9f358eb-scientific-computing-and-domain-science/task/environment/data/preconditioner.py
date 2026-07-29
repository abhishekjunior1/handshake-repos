"""
Preconditioner Module

Implements preconditioning strategies for the conjugate gradient method.
Preconditioning transforms the linear system to improve the condition number,
accelerating convergence of iterative solvers.

Supported preconditioners:
- Jacobi (diagonal scaling): M = diag(A)
- SSOR (Symmetric Successive Over-Relaxation): approximate factorization

The Jacobi preconditioner is the default choice for diagonally dominant systems
where the diagonal entries dominate off-diagonal coupling.
"""

import math


def build_preconditioner(A, preconditioner_type="jacobi"):
    """
    Build a preconditioner from the system matrix.

    The preconditioner M approximates A^{-1} such that M*A has a smaller
    condition number than A alone. For Jacobi, M = diag(A)^{-1}.

    Parameters
    ----------
    A : dict
        CSR sparse matrix representation.
    preconditioner_type : str
        Type of preconditioner: "jacobi" or "ssor".

    Returns
    -------
    dict
        Preconditioner data structure with type-specific fields:
        - For Jacobi: {"type": "jacobi", "inv_diag": [...], "n": int}
        - For SSOR: {"type": "ssor", "factors": {...}, "n": int}
    """
    n = A["n"]

    if preconditioner_type == "jacobi":
        return _build_jacobi(A, n)
    elif preconditioner_type == "ssor":
        return _build_ssor(A, n)
    else:
        raise ValueError(f"Unknown preconditioner type: {preconditioner_type}")


def _build_jacobi(A, n):
    """
    Build Jacobi (diagonal) preconditioner.

    Extracts diagonal of A and computes element-wise inverse.
    For SPD matrices, all diagonal entries are positive, so the
    inverse is well-defined.

    Parameters
    ----------
    A : dict
        CSR sparse matrix.
    n : int
        Matrix dimension.

    Returns
    -------
    dict
        Jacobi preconditioner with inverse diagonal entries.
    """
    row_ptr = A["row_ptr"]
    col_idx = A["col_idx"]
    values = A["values"]

    inv_diag = [0.0] * n

    for i in range(n):
        row_start = row_ptr[i]
        row_end = row_ptr[i + 1]
        diag_val = 0.0

        for j in range(row_start, row_end):
            if col_idx[j] == i:
                diag_val = values[j]
                break

        if abs(diag_val) < 1e-15:
            # Fallback for near-zero diagonal (shouldn't happen for SPD)
            inv_diag[i] = 1.0
        else:
            inv_diag[i] = 1.0 / diag_val

    return {
        "type": "jacobi",
        "inv_diag": inv_diag,
        "n": n,
    }


def _build_ssor(A, n):
    """
    Build SSOR preconditioner with relaxation parameter omega=1.0.

    SSOR uses the splitting A = D + L + L^T where D is diagonal and L is
    strictly lower triangular. The preconditioner is:
    M^{-1} = (D + L) D^{-1} (D + L^T)

    For simplicity, stores the lower triangular factor and diagonal.

    Parameters
    ----------
    A : dict
        CSR sparse matrix.
    n : int
        Matrix dimension.

    Returns
    -------
    dict
        SSOR preconditioner with triangular factors.
    """
    row_ptr = A["row_ptr"]
    col_idx = A["col_idx"]
    values = A["values"]

    # Extract diagonal and lower triangular entries
    diag = [0.0] * n
    lower = {}  # (i, j) -> value for j < i

    for i in range(n):
        row_start = row_ptr[i]
        row_end = row_ptr[i + 1]
        for k in range(row_start, row_end):
            j = col_idx[k]
            v = values[k]
            if j == i:
                diag[i] = v
            elif j < i:
                lower[(i, j)] = v

    return {
        "type": "ssor",
        "diag": diag,
        "lower": lower,
        "n": n,
    }


def apply_preconditioner(M, r):
    """
    Apply preconditioner to a vector: z = M^{-1} * r.

    For Jacobi: z_i = r_i / A_{ii} (element-wise diagonal scaling).
    For SSOR: forward-backward triangular solve.

    Parameters
    ----------
    M : dict
        Preconditioner data structure from build_preconditioner.
    r : list[float]
        Input vector (typically the residual).

    Returns
    -------
    list[float]
        Preconditioned vector z = M^{-1} * r.
    """
    if M["type"] == "jacobi":
        return _apply_jacobi(M, r)
    elif M["type"] == "ssor":
        return _apply_ssor(M, r)
    else:
        raise ValueError(f"Unknown preconditioner type: {M['type']}")


def _apply_jacobi(M, r):
    """
    Apply Jacobi preconditioner: z_i = r_i * (1/A_{ii}).

    This is the simplest possible preconditioner — diagonal scaling.
    Effective when the matrix is diagonally dominant.

    Parameters
    ----------
    M : dict
        Jacobi preconditioner with inv_diag field.
    r : list[float]
        Input vector.

    Returns
    -------
    list[float]
        Scaled vector.
    """
    inv_diag = M["inv_diag"]
    n = M["n"]
    z = [r[i] * inv_diag[i] for i in range(n)]
    return z


def _apply_ssor(M, r):
    """
    Apply SSOR preconditioner via forward and backward sweeps.

    Forward solve: (D + L) y = r
    Diagonal scale: w = D * y
    Backward solve: (D + L^T) z = w

    Parameters
    ----------
    M : dict
        SSOR preconditioner with diag and lower fields.
    r : list[float]
        Input vector.

    Returns
    -------
    list[float]
        Preconditioned vector.
    """
    n = M["n"]
    diag = M["diag"]
    lower = M["lower"]

    # Forward sweep: (D + L) y = r
    y = [0.0] * n
    for i in range(n):
        s = r[i]
        for j in range(i):
            if (i, j) in lower:
                s -= lower[(i, j)] * y[j]
        y[i] = s / diag[i]

    # Diagonal scaling: w = D * y
    w = [diag[i] * y[i] for i in range(n)]

    # Backward sweep: (D + L^T) z = w
    z = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = w[i]
        for j in range(i + 1, n):
            if (j, i) in lower:
                s -= lower[(j, i)] * z[j]
        z[i] = s / diag[i]

    return z


def get_preconditioner_info(M):
    """
    Get summary information about the preconditioner.

    Parameters
    ----------
    M : dict
        Preconditioner data structure.

    Returns
    -------
    dict
        Summary with type, dimension, and conditioning info.
    """
    info = {
        "type": M["type"],
        "dimension": M["n"],
    }

    if M["type"] == "jacobi":
        inv_diag = M["inv_diag"]
        diag_min = 1.0 / max(inv_diag) if max(inv_diag) > 0 else float("inf")
        diag_max = 1.0 / min(inv_diag) if min(inv_diag) > 0 else float("inf")
        info["diagonal_condition"] = diag_max / diag_min if diag_min > 0 else float("inf")

    return info
