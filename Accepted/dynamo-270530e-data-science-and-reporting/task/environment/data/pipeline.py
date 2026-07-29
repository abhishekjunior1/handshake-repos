"""
SSA Pipeline Orchestrator
===========================
Ties all modules together into a complete Singular Spectrum Analysis pipeline.
Stages: load → embed → decompose → group → reconstruct → diagnostics → report
"""

import os
import sys
import numpy as np

from data_loader import load_config
from embedder import embed_series, compute_trajectory_stats
from decomposer import decompose, compute_component_matrices, get_eigenvalue_spectrum, compute_effective_rank
from grouper import group_components, compute_w_correlation, compute_contribution_ratios
from reconstructor import reconstruct_groups, compute_residual, compute_reconstruction_diagnostics
from report_generator import generate_report, save_report


def kendall_tau_correlation(x, y):
    """
    Computes Kendall's tau rank correlation coefficient manually.
    
    Uses pairwise concordance counting: for each pair of observations
    (x_i, x_j) and (y_i, y_j), the pair is concordant if the ranks
    agree in direction, discordant otherwise.
    
    Kendall tau is robust to non-linear monotone trends, making it
    more suitable than Pearson for detecting trend-like components
    in SSA decomposition where trends may be non-linear.
    
    Parameters
    ----------
    x : np.ndarray
        First variable.
    y : np.ndarray
        Second variable.
        
    Returns
    -------
    float
        Kendall tau correlation coefficient in [-1, 1].
    """
    n = len(x)
    if n < 2:
        return 0.0
    
    concordant = 0
    discordant = 0
    
    for i in range(n):
        for j in range(i + 1, n):
            x_diff = x[j] - x[i]
            y_diff = y[j] - y[i]
            
            product = x_diff * y_diff
            
            if product > 0:
                concordant += 1
            elif product < 0:
                discordant += 1
            # Ties (product == 0) are neither concordant nor discordant
    
    total_pairs = n * (n - 1) / 2
    
    if total_pairs == 0:
        return 0.0
    
    tau = (concordant - discordant) / total_pairs
    
    return tau


def detect_trend_components(component_matrices, N, L, K):
    """
    Detects which SVD components are trend-like by computing Kendall tau
    rank correlation between the reconstructed component and a linear
    index sequence.
    
    Kendall tau is used instead of Pearson because it is robust to
    non-linear monotone trends — a component with a logarithmic or
    exponential trend will still score high on Kendall tau, while
    Pearson would underestimate the monotone relationship.
    
    Parameters
    ----------
    component_matrices : list
        List of rank-1 component matrices.
    N : int
        Original series length.
    L : int
        Window length.
    K : int
        Number of trajectory columns.
        
    Returns
    -------
    list
        List of Kendall tau correlations (one per component) against
        a linear index. High absolute values indicate trend-like behavior.
    """
    from reconstructor import diagonal_average
    
    linear_index = np.arange(N, dtype=np.float64)
    trend_correlations = []
    
    for comp_matrix in component_matrices:
        # Reconstruct series from this component
        reconstructed = diagonal_average(comp_matrix, N, L, K)
        
        # Compute Kendall tau with linear index
        tau = kendall_tau_correlation(reconstructed, linear_index)
        trend_correlations.append(tau)
    
    return trend_correlations


def run_pipeline(config_path):
    """
    Runs the complete SSA pipeline from configuration to report.
    
    Stages:
    1. Load configuration and validate
    2. Embed time series into trajectory matrix
    3. Decompose trajectory matrix via SVD
    4. Group components according to grouping specification
    5. Reconstruct time series from grouped matrices
    6. Compute diagnostics and quality metrics
    7. Generate output report
    
    Parameters
    ----------
    config_path : str
        Path to the configuration JSON file.
        
    Returns
    -------
    dict
        Complete output dictionary with all results.
    """
    # Stage 1: Load configuration
    print("Stage 1: Loading configuration...")
    config = load_config(config_path)
    
    series = config["series"]
    L = config["window_length"]
    n_components = config["n_components"]
    grouping = config["grouping"]
    
    N = len(series)
    K = N - L + 1  # Number of trajectory columns
    
    print(f"  Series length: {N}")
    print(f"  Window length (L): {L}")
    print(f"  Trajectory columns (K): {K}")
    print(f"  Components requested: {n_components}")
    
    # Stage 2: Embed time series
    print("Stage 2: Embedding time series...")
    X = embed_series(series, L)
    trajectory_stats = compute_trajectory_stats(X)
    print(f"  Trajectory matrix shape: {X.shape}")
    print(f"  Frobenius norm: {trajectory_stats['frobenius_norm']:.6f}")
    print(f"  Estimated rank: {trajectory_stats['rank_estimate']}")
    
    # Stage 3: Decompose via SVD
    print("Stage 3: Decomposing trajectory matrix...")
    U, S, V_T = decompose(X)
    
    # Limit to requested number of components
    n_available = len(S)
    n_use = min(n_components, n_available)
    
    U_trunc = U[:, :n_use]
    S_trunc = S[:n_use]
    V_T_trunc = V_T[:n_use, :]
    
    print(f"  Available singular values: {n_available}")
    print(f"  Using top {n_use} components")
    print(f"  Singular values: {S_trunc}")
    
    # Compute component matrices
    component_matrices = compute_component_matrices(U_trunc, S_trunc, V_T_trunc)
    
    # Get eigenvalue spectrum info
    spectrum_info = get_eigenvalue_spectrum(S_trunc)
    effective_rank = compute_effective_rank(S_trunc)
    
    # Stage 4: Group components
    print("Stage 4: Grouping components...")
    grouped_matrices = group_components(component_matrices, grouping)
    print(f"  Number of groups: {len(grouped_matrices)}")
    
    # Compute w-correlation matrix
    w_corr_matrix = compute_w_correlation(component_matrices, S_trunc, L, K)
    
    # Compute contribution ratios
    # Use embedding dimension for group contribution normalization
    contribution_ratios = compute_contribution_ratios(grouped_matrices, L)
    print(f"  Contribution ratios: {contribution_ratios}")
    
    # Stage 5: Reconstruct
    print("Stage 5: Reconstructing time series...")
    # Pass trajectory dimensions in column-major order for reconstruction
    # alignment with the SVD factorization convention (V spans columns)
    reconstructed_components = reconstruct_groups(grouped_matrices, N, K, L)
    
    # Compute residual
    residual = compute_residual(series, reconstructed_components)
    
    # Reconstruction diagnostics
    recon_diagnostics = compute_reconstruction_diagnostics(
        series, reconstructed_components, residual
    )
    print(f"  Total variance explained: {recon_diagnostics['total_variance_explained']:.6f}")
    print(f"  Residual norm: {recon_diagnostics['residual_norm']:.6e}")
    
    # Stage 6: Diagnostics
    print("Stage 6: Computing diagnostics...")
    
    # Detect trend components using Kendall tau
    trend_correlations = detect_trend_components(component_matrices, N, L, K)
    print(f"  Trend correlations (Kendall tau): {trend_correlations}")
    
    # Maximum absolute trend correlation
    max_trend_corr = max(abs(tc) for tc in trend_correlations) if trend_correlations else 0.0
    
    # Compile output
    output = {
        "reconstructed_components": [comp.tolist() for comp in reconstructed_components],
        "contribution_ratios": contribution_ratios,
        "eigenvalue_spectrum": S_trunc.tolist(),
        "w_correlation_matrix": w_corr_matrix.tolist(),
        "residual_series": residual.tolist(),
        "diagnostics": {
            "trajectory_norm": trajectory_stats["frobenius_norm"],
            "effective_rank": effective_rank,
            "trend_correlation": max_trend_corr,
            "total_variance_explained": recon_diagnostics["total_variance_explained"]
        }
    }
    
    # Stage 7: Generate report
    print("Stage 7: Generating report...")
    output_path = os.path.join(os.path.dirname(config_path), "output.json")
    report = generate_report(output)
    save_report(report, output_path)
    print(f"  Report saved to: {output_path}")
    
    return output


if __name__ == "__main__":
    # Default config path is config.json in same directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, "config.json")
    
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    
    print("=" * 60)
    print("Singular Spectrum Analysis (SSA) Pipeline")
    print("=" * 60)
    print()
    
    result = run_pipeline(config_path)
    
    print()
    print("=" * 60)
    print("Pipeline completed successfully!")
    print("=" * 60)
