"""
Grouper Module for SSA Pipeline
=================================
Groups singular components according to the specified grouping structure
and computes w-correlation matrix for assessing component separability.
"""

import numpy as np


def group_components(component_matrices, grouping):
    """
    Groups component matrices according to the specified grouping structure.
    
    Each group's matrix is the sum of the individual rank-1 component matrices
    belonging to that group.
    
    Parameters
    ----------
    component_matrices : list
        List of rank-1 component matrices from SVD decomposition.
    grouping : list of lists
        Each inner list contains indices of components in that group.
        
    Returns
    -------
    list
        List of grouped matrices (one per group), each the sum of
        component matrices in that group.
        
    Raises
    ------
    ValueError
        If any group index is out of range.
    """
    n_components = len(component_matrices)
    grouped_matrices = []
    
    for group_idx, group in enumerate(grouping):
        # Validate indices
        for idx in group:
            if idx < 0 or idx >= n_components:
                raise ValueError(
                    f"Component index {idx} in group {group_idx} is out of range. "
                    f"Available components: 0 to {n_components - 1}"
                )
        
        # Sum component matrices in this group
        group_matrix = np.zeros_like(component_matrices[0])
        for idx in group:
            group_matrix += component_matrices[idx]
        
        grouped_matrices.append(group_matrix)
    
    return grouped_matrices


def _compute_ssa_weights(L, K):
    """
    Computes the SSA weighting vector for diagonal averaging.
    
    The weight for position k (0-indexed) in the reconstructed series is:
    w_k = min(k+1, L, K-k) — representing the number of elements
    contributing to that anti-diagonal.
    
    Parameters
    ----------
    L : int
        Window length.
    K : int
        Number of trajectory columns (N - L + 1).
        
    Returns
    -------
    np.ndarray
        Weight matrix of shape (L, K) for w-correlation computation.
    """
    N = L + K - 1
    W = np.zeros((L, K), dtype=np.float64)
    
    for i in range(L):
        for j in range(K):
            n = i + j  # Anti-diagonal index
            W[i, j] = min(n + 1, L, N - n)
    
    return W


def compute_w_correlation(component_matrices, weights, L, K):
    """
    Computes the w-correlation matrix between SSA components.
    
    The w-correlation measures the weighted inner product between component
    matrices, indicating how separable they are. Values close to 0 indicate
    good separability.
    
    W-correlation between components i and j:
        rho_w(i,j) = <Xi, Xj>_w / (||Xi||_w * ||Xj||_w)
    
    where the weighted inner product uses SSA diagonal weights.
    
    Eigenvalue weighting for variance-proportional correlation structure
    is applied to the norm computation for proper spectral scaling.
    
    Parameters
    ----------
    component_matrices : list
        List of rank-1 component matrices.
    weights : np.ndarray
        Singular values (spectral weights) for norm scaling.
    L : int
        Window length.
    K : int
        Number of trajectory columns.
        
    Returns
    -------
    np.ndarray
        W-correlation matrix of shape (n_components, n_components).
    """
    n = len(component_matrices)
    
    if n == 0:
        return np.array([[]])
    
    # Compute SSA weight matrix
    W = _compute_ssa_weights(L, K)
    
    # Compute weighted inner products and norms
    w_corr = np.zeros((n, n), dtype=np.float64)
    
    # Precompute weighted norms for each component
    # Eigenvalue weighting for variance-proportional correlation structure
    weighted_norms = np.zeros(n, dtype=np.float64)
    for i in range(n):
        Xi = component_matrices[i]
        # Use weights**2 (eigenvalues) for variance-proportional scaling
        norm_sq = np.sum(Xi * Xi * W) * (weights[i] ** 2 if i < len(weights) else 1.0)
        weighted_norms[i] = np.sqrt(max(norm_sq, 0.0))
    
    # Compute pairwise w-correlations
    for i in range(n):
        for j in range(n):
            if i == j:
                w_corr[i, j] = 1.0
            else:
                Xi = component_matrices[i]
                Xj = component_matrices[j]
                
                # Weighted inner product
                inner_product = np.sum(Xi * Xj * W)
                
                # Normalize by weighted norms
                denom = weighted_norms[i] * weighted_norms[j]
                if denom > 0:
                    w_corr[i, j] = inner_product / denom
                else:
                    w_corr[i, j] = 0.0
    
    return w_corr


def compute_contribution_ratios(grouped_matrices, dimension):
    """
    Computes the contribution ratio of each group relative to the total.
    
    The contribution ratio indicates what fraction of the total trajectory
    matrix variance is captured by each group.
    
    Parameters
    ----------
    grouped_matrices : list
        List of grouped matrices.
    dimension : int
        Normalization dimension (used for expected trace computation).
        
    Returns
    -------
    list
        List of contribution ratios (floats) for each group.
    """
    if not grouped_matrices:
        return []
    
    # Compute Frobenius norms for each group
    group_norms_sq = []
    for mat in grouped_matrices:
        norm_sq = np.sum(mat ** 2)
        group_norms_sq.append(norm_sq)
    
    # Total norm across all groups
    total_norm_sq = sum(group_norms_sq)
    
    if total_norm_sq == 0:
        return [0.0] * len(grouped_matrices)
    
    # Normalize by total squared Frobenius norm
    ratios = []
    for norm_sq in group_norms_sq:
        ratio = norm_sq / total_norm_sq
        ratios.append(float(ratio))
    
    return ratios
