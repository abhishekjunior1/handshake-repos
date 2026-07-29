"""
Matrix Operations Module

Provides sparse matrix construction and fundamental linear algebra operations
for the PCG solver. Uses compressed sparse row (CSR) representation internally
for efficient matrix-vector products.

Supports COO (coordinate) input format conversion to CSR for computation.
"""

import math


def build_sparse_matrix(coo_data, dimension):
    """
    Build a CSR sparse matrix from COO (coordinate) format input.

    The COO format provides three parallel arrays: row indices, column indices,
    and values. This function converts to CSR for efficient row-based access
    during matrix-vector products.

    Parameters
    ----------
    coo_data : dict
        Dictionary with keys "rows", "cols", "values" — parallel arrays
        defining non-zero entries in coordinate format.
    dimension : int
        Matrix dimension (n for an nxn matrix).

    Returns
    -------
    dict
        CSR representation with keys:
        - "row_ptr": list[int] of length n+1, cumulative non-zeros per row
        - "col_idx": list[int], column indices of non-zeros
        - "values": list[float], non-zero values
        - "n": int, matrix dimension
    """
    rows = coo_data["rows"]
    cols = coo_data["cols"]
    values = coo_data["values"]
    n = dimension

    # Count entries per row
    row_counts = [0] * n
    for r in rows:
        row_counts[r] += 1

    # Build row_ptr (cumulative sum)
    row_ptr = [0] * (n + 1)
    for i in range(n):
        row_ptr[i + 1] = row_ptr[i] + row_counts[i]

    # Fill column indices and values in row-major order
    nnz = len(values)
    col_idx = [0] * nnz
    csr_values = [0.0] * nnz

    # Track current insertion position per row
    current_pos = row_ptr[:]

    for i in range(nnz):
        r = rows[i]
        pos = current_pos[r]
        col_idx[pos] = cols[i]
        csr_values[pos] = values[i]
        current_pos[r] += 1

    # Sort columns within each row for consistent access patterns
    for i in range(n):
        start = row_ptr[i]
        end = row_ptr[i + 1]
        # Insertion sort (rows are typically short in sparse matrices)
        for j in range(start + 1, end):
            key_col = col_idx[j]
            key_val = csr_values[j]
            k = j - 1
            while k >= start and col_idx[k] > key_col:
                col_idx[k + 1] = col_idx[k]
                csr_values[k + 1] = csr_values[k]
                k -= 1
            col_idx[k + 1] = key_col
            csr_values[k + 1] = key_val

    return {
        "row_ptr": row_ptr,
        "col_idx": col_idx,
        "values": csr_values,
        "n": n,
    }


def matrix_vector_product(A, x):
    """
    Compute sparse matrix-vector product y = A * x.

    Uses CSR format for efficient row-wise dot products. Each row's
    contribution is computed by iterating only over non-zero entries.

    Parameters
    ----------
    A : dict
        CSR sparse matrix (from build_sparse_matrix).
    x : list[float]
        Input vector of length n.

    Returns
    -------
    list[float]
        Result vector y = A*x of length n.
    """
    n = A["n"]
    row_ptr = A["row_ptr"]
    col_idx = A["col_idx"]
    values = A["values"]

    y = [0.0] * n
    for i in range(n):
        row_start = row_ptr[i]
        row_end = row_ptr[i + 1]
        acc = 0.0
        for j in range(row_start, row_end):
            acc += values[j] * x[col_idx[j]]
        y[i] = acc

    return y


def compute_residual(A, x, b):
    """
    Compute the residual vector r = b - A*x.

    The residual measures how far the current approximate solution x
    is from satisfying the linear system Ax = b. A zero residual
    indicates an exact solution.

    Parameters
    ----------
    A : dict
        CSR sparse matrix.
    x : list[float]
        Current approximate solution.
    b : list[float]
        Right-hand side vector.

    Returns
    -------
    list[float]
        Residual vector r = b - Ax.
    """
    Ax = matrix_vector_product(A, x)
    n = len(b)
    r = [b[i] - Ax[i] for i in range(n)]
    return r


def vector_norm(v):
    """
    Compute the Euclidean (L2) norm of a vector.

    Parameters
    ----------
    v : list[float]
        Input vector.

    Returns
    -------
    float
        ||v||_2 = sqrt(sum(v_i^2))
    """
    return math.sqrt(sum(vi * vi for vi in v))


def vector_dot(a, b):
    """
    Compute dot product of two vectors.

    Parameters
    ----------
    a : list[float]
        First vector.
    b : list[float]
        Second vector.

    Returns
    -------
    float
        a · b = sum(a_i * b_i)
    """
    return sum(ai * bi for ai, bi in zip(a, b))


def extract_diagonal(A):
    """
    Extract the diagonal entries of a sparse matrix.

    Parameters
    ----------
    A : dict
        CSR sparse matrix.

    Returns
    -------
    list[float]
        Diagonal entries [A[0,0], A[1,1], ..., A[n-1,n-1]].
    """
    n = A["n"]
    row_ptr = A["row_ptr"]
    col_idx = A["col_idx"]
    values = A["values"]

    diag = [0.0] * n
    for i in range(n):
        row_start = row_ptr[i]
        row_end = row_ptr[i + 1]
        for j in range(row_start, row_end):
            if col_idx[j] == i:
                diag[i] = values[j]
                break

    return diag


def get_matrix_properties(A):
    """
    Compute basic properties of the sparse matrix.

    Parameters
    ----------
    A : dict
        CSR sparse matrix.

    Returns
    -------
    dict
        Properties including dimension, nnz, density, diagonal range.
    """
    n = A["n"]
    nnz = len(A["values"])
    density = nnz / (n * n) if n > 0 else 0.0

    diag = extract_diagonal(A)
    diag_min = min(diag) if diag else 0.0
    diag_max = max(diag) if diag else 0.0

    return {
        "dimension": n,
        "nnz": nnz,
        "density": density,
        "diagonal_min": diag_min,
        "diagonal_max": diag_max,
    }
