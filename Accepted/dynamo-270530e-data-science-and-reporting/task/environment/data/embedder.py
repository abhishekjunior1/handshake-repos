"""
Embedder Module for SSA Pipeline
==================================
Creates the trajectory (Hankel) matrix from the time series
by embedding it into a delay coordinate space.
"""

import numpy as np


def embed_series(series, L):
    """
    Constructs the trajectory matrix (Hankel matrix) from the time series.
    
    The trajectory matrix X has shape (L, K) where K = N - L + 1.
    Each column j is a lagged window: X[:, j] = series[j:j+L]
    
    Parameters
    ----------
    series : np.ndarray
        Input time series of length N.
    L : int
        Window length (embedding dimension).
        
    Returns
    -------
    np.ndarray
        Trajectory matrix of shape (L, K).
        
    Raises
    ------
    ValueError
        If window length is invalid for the given series.
    """
    N = len(series)
    
    if L < 2:
        raise ValueError(f"Window length must be at least 2, got {L}")
    if L >= N:
        raise ValueError(f"Window length {L} must be less than series length {N}")
    
    K = N - L + 1  # Number of lagged vectors (columns)
    
    # Construct trajectory matrix using lagged windows
    # Each column j contains the subsequence series[j:j+L]
    X = np.zeros((L, K), dtype=np.float64)
    
    for j in range(K):
        X[:, j] = series[j:j + L]
    
    return X


def compute_trajectory_stats(X):
    """
    Computes statistics of the trajectory matrix for diagnostics.
    
    Parameters
    ----------
    X : np.ndarray
        Trajectory matrix of shape (L, K).
        
    Returns
    -------
    dict
        Dictionary containing:
        - frobenius_norm: float, Frobenius norm of X
        - spectral_norm: float, largest singular value approximation
        - rank_estimate: int, numerical rank estimate
        - shape: tuple, (L, K) dimensions
        - mean_column_norm: float, average L2 norm of columns
    """
    L, K = X.shape
    
    # Frobenius norm
    frobenius_norm = np.linalg.norm(X, 'fro')
    
    # Spectral norm approximation via power iteration
    # Use a few iterations for a rough estimate
    v = np.random.randn(K)
    v = v / np.linalg.norm(v)
    for _ in range(10):
        u = X @ v
        u_norm = np.linalg.norm(u)
        if u_norm > 0:
            u = u / u_norm
        v = X.T @ u
        v_norm = np.linalg.norm(v)
        if v_norm > 0:
            v = v / v_norm
    spectral_norm = np.linalg.norm(X @ v)
    
    # Numerical rank estimate using tolerance
    # Based on singular value threshold relative to largest
    tolerance = max(L, K) * np.finfo(np.float64).eps * spectral_norm
    singular_values = np.linalg.svd(X, compute_uv=False)
    rank_estimate = int(np.sum(singular_values > tolerance))
    
    # Column norms
    column_norms = np.linalg.norm(X, axis=0)
    mean_column_norm = np.mean(column_norms)
    
    stats = {
        "frobenius_norm": float(frobenius_norm),
        "spectral_norm": float(spectral_norm),
        "rank_estimate": rank_estimate,
        "shape": (L, K),
        "mean_column_norm": float(mean_column_norm)
    }
    
    return stats
