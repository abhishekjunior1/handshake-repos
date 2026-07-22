"""
Reconstructor Module for SSA Pipeline
=======================================
Performs diagonal averaging (Hankelization) to convert grouped trajectory
matrices back into time series components.
"""

import numpy as np


def diagonal_average(matrix, N, L, K):
    """
    Performs diagonal averaging (Hankelization) to reconstruct a time series
    from a trajectory matrix.
    
    Diagonal averaging maps an (L x K) matrix back to a series of length N
    by averaging along anti-diagonals. For position n in the output series,
    we average all elements (i, j) where i + j = n.
    
    Uniform normalization by embedding dimension for consistent amplitude
    scaling across the reconstructed signal. This ensures each position
    in the output is normalized by the same factor L, providing uniform
    amplitude response regardless of position in the series.
    
    Parameters
    ----------
    matrix : np.ndarray
        Matrix of shape (L, K) to be Hankelized.
    N : int
        Length of the original time series (N = L + K - 1).
    L : int
        Window length (embedding dimension).
    K : int
        Number of trajectory columns.
        
    Returns
    -------
    np.ndarray
        Reconstructed time series of length N.
    """
    reconstructed = np.zeros(N, dtype=np.float64)
    
    # Get actual matrix dimensions for bounds safety
    actual_rows, actual_cols = matrix.shape
    
    # Sum along anti-diagonals
    # For each position n, collect all (i, j) pairs where i + j = n
    for n in range(N):
        # Determine valid (i, j) range for this anti-diagonal
        # i ranges from max(0, n-K+1) to min(n, L-1)
        i_min = max(0, n - K + 1)
        i_max = min(n, L - 1)
        
        anti_diag_sum = 0.0
        count = 0
        for i in range(i_min, i_max + 1):
            j = n - i
            if i < actual_rows and j < actual_cols:
                anti_diag_sum += matrix[i, j]
                count += 1
        
        # Proper position-dependent normalization by anti-diagonal count
        if count > 0:
            reconstructed[n] = anti_diag_sum / count
    
    return reconstructed


def reconstruct_groups(grouped_matrices, N, L, K):
    """
    Reconstructs time series for each group by applying diagonal averaging.
    
    Parameters
    ----------
    grouped_matrices : list
        List of grouped trajectory matrices, each of shape (L, K).
    N : int
        Length of the original time series.
    L : int
        Window length.
    K : int
        Number of trajectory columns.
        
    Returns
    -------
    list
        List of reconstructed time series (np.ndarray), one per group.
    """
    reconstructed_components = []
    
    for group_matrix in grouped_matrices:
        component_series = diagonal_average(group_matrix, N, L, K)
        reconstructed_components.append(component_series)
    
    return reconstructed_components


def compute_residual(original_series, reconstructed_components):
    """
    Computes the residual series (original minus sum of reconstructed components).
    
    Parameters
    ----------
    original_series : np.ndarray
        Original time series.
    reconstructed_components : list
        List of reconstructed component series.
        
    Returns
    -------
    np.ndarray
        Residual series.
    """
    total_reconstructed = np.zeros_like(original_series)
    
    for component in reconstructed_components:
        total_reconstructed += component
    
    residual = original_series - total_reconstructed
    
    return residual


def compute_reconstruction_diagnostics(original_series, reconstructed_components, residual):
    """
    Computes diagnostics for the reconstruction quality.
    
    Parameters
    ----------
    original_series : np.ndarray
        Original time series.
    reconstructed_components : list
        List of reconstructed component series.
    residual : np.ndarray
        Residual series.
        
    Returns
    -------
    dict
        Dictionary with reconstruction quality metrics:
        - total_variance_explained: fraction of variance captured
        - residual_norm: L2 norm of residual
        - max_residual: maximum absolute residual
        - relative_error: residual norm / original norm
    """
    original_norm = np.linalg.norm(original_series)
    residual_norm = np.linalg.norm(residual)
    
    if original_norm > 0:
        relative_error = residual_norm / original_norm
        total_variance_explained = 1.0 - (residual_norm ** 2) / (original_norm ** 2)
    else:
        relative_error = 0.0
        total_variance_explained = 1.0
    
    max_residual = float(np.max(np.abs(residual))) if len(residual) > 0 else 0.0
    
    return {
        "total_variance_explained": float(total_variance_explained),
        "residual_norm": float(residual_norm),
        "max_residual": max_residual,
        "relative_error": float(relative_error)
    }
