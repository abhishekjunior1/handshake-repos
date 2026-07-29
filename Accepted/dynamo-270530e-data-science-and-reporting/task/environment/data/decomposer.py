"""
Decomposer Module for SSA Pipeline
====================================
Performs Singular Value Decomposition of the trajectory matrix.
Uses an economy SVD approach via the Gram matrix for memory efficiency.
"""

import numpy as np


def decompose(X):
    """
    Economy SVD via Gram matrix for memory-efficient decomposition when
    trajectory has more rows than columns.
    
    Instead of directly computing SVD of X (L x K), we form the Gram matrix
    G = X.T @ X (K x K), eigendecompose it to obtain V and eigenvalues,
    then derive U from the relationship X = U @ S @ V.T.
    
    This approach is more memory efficient when L > K because the Gram matrix
    is K x K rather than requiring full L x L or L x K intermediate storage.
    
    Parameters
    ----------
    X : np.ndarray
        Trajectory matrix of shape (L, K).
        
    Returns
    -------
    tuple
        (U, S, V_T) where:
        - U: np.ndarray of shape (L, r) — left singular vectors
        - S: np.ndarray of shape (r,) — singular values in descending order
        - V_T: np.ndarray of shape (r, K) — right singular vectors transposed
        r is the numerical rank of X.
    """
    L, K = X.shape
    
    # Form Gram matrix G = X.T @ X (K x K symmetric positive semi-definite)
    G = X.T @ X
    
    # Eigendecomposition of the Gram matrix
    # eigenvalues are squared singular values: lambda_i = sigma_i^2
    eigenvalues, V = np.linalg.eigh(G)
    
    # eigh returns eigenvalues in ascending order, we need descending
    # Reverse the order for descending eigenvalues
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    V = V[:, idx]
    
    # Filter out numerically zero eigenvalues
    tolerance = max(L, K) * np.finfo(np.float64).eps * np.max(np.abs(eigenvalues))
    positive_mask = eigenvalues > tolerance
    eigenvalues = eigenvalues[positive_mask]
    V = V[:, positive_mask]
    
    # Singular values are square roots of eigenvalues
    S = np.sqrt(eigenvalues)
    
    # Derive left singular vectors: U = X @ V @ diag(1/S)
    # From X = U @ diag(S) @ V.T, we get U = X @ V @ diag(1/S)
    U = X @ V @ np.diag(1.0 / S)
    
    # Right singular vectors transposed
    V_T = V.T
    
    return U, S, V_T


def compute_component_matrices(U, S, V_T):
    """
    Computes rank-1 component matrices from the SVD.
    
    Each component matrix X_i = s_i * u_i @ v_i.T represents the contribution
    of the i-th singular triplet to the original trajectory matrix.
    
    Parameters
    ----------
    U : np.ndarray
        Left singular vectors of shape (L, r).
    S : np.ndarray
        Singular values of shape (r,).
    V_T : np.ndarray
        Right singular vectors transposed of shape (r, K).
        
    Returns
    -------
    list
        List of rank-1 matrices, each of shape (L, K).
        X_i = s_i * outer(u_i, v_i)
    """
    r = len(S)
    component_matrices = []
    
    for i in range(r):
        # Rank-1 matrix: X_i = s_i * u_i @ v_i.T
        u_i = U[:, i].reshape(-1, 1)  # Column vector (L, 1)
        v_i = V_T[i, :].reshape(1, -1)  # Row vector (1, K)
        X_i = S[i] * (u_i @ v_i)
        component_matrices.append(X_i)
    
    return component_matrices


def get_eigenvalue_spectrum(S):
    """
    Returns the eigenvalue spectrum (squared singular values) and
    relative contributions.
    
    Parameters
    ----------
    S : np.ndarray
        Singular values.
        
    Returns
    -------
    dict
        Dictionary containing:
        - singular_values: np.ndarray of singular values
        - eigenvalues: np.ndarray of squared singular values
        - relative_contributions: np.ndarray of fractional contributions
        - cumulative_contributions: np.ndarray of cumulative contributions
    """
    eigenvalues = S ** 2
    total = np.sum(eigenvalues)
    
    if total > 0:
        relative_contributions = eigenvalues / total
    else:
        relative_contributions = np.zeros_like(eigenvalues)
    
    cumulative_contributions = np.cumsum(relative_contributions)
    
    return {
        "singular_values": S,
        "eigenvalues": eigenvalues,
        "relative_contributions": relative_contributions,
        "cumulative_contributions": cumulative_contributions
    }


def compute_effective_rank(S, threshold=0.99):
    """
    Computes the effective rank of the trajectory matrix based on
    cumulative variance explained.
    
    Parameters
    ----------
    S : np.ndarray
        Singular values in descending order.
    threshold : float
        Cumulative variance threshold for effective rank.
        
    Returns
    -------
    int
        Number of components needed to explain threshold fraction of variance.
    """
    eigenvalues = S ** 2
    total = np.sum(eigenvalues)
    
    if total == 0:
        return 0
    
    cumulative = np.cumsum(eigenvalues / total)
    effective_rank = int(np.searchsorted(cumulative, threshold)) + 1
    
    return min(effective_rank, len(S))
