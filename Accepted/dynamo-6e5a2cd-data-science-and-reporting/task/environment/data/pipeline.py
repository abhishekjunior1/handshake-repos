"""
Extreme Value Analysis (EVA) Pipeline

Performs peaks-over-threshold analysis with temporal declustering,
fits generalized Pareto distributions, and estimates multi-period
return levels for extreme event characterization.

Usage:
    python3 pipeline.py <input_file> <output_file>
"""

import sys
import os

from data_loader import load_input_data, extract_exceedances
from block_maxima import extract_block_maxima, fit_gev, compute_block_summary
from declustering import run_declustering
from shape_estimator import estimate_gpd_parameters
from return_level import compute_all_return_levels
from diagnostics import (compute_qq_statistics, compute_goodness_of_fit,
                         compute_diagnostic_flags)
from output_formatter import format_output, write_output


def run_pipeline(input_path: str, output_path: str) -> None:
    """
    Execute the complete EVA pipeline.

    Processes observation data through block maxima analysis, threshold
    exceedance extraction, temporal declustering, GPD fitting, return
    level computation, and diagnostic assessment.

    Parameters
    ----------
    input_path : str
        Path to JSON input data file.
    output_path : str
        Path for JSON output results.
    """
    # =========================================================================
    # Stage 1: Load and validate input data
    # =========================================================================
    print("Stage 1: Loading input data...")
    config = load_input_data(input_path)

    observations = config["observations"]
    threshold = config["threshold"]
    run_length = config["run_length"]
    return_periods = config["return_periods"]
    block_size = config["block_size"]
    confidence_level = config["confidence_level"]
    n_total = len(observations)

    print(f"  Loaded {n_total} observations, threshold={threshold}")

    # =========================================================================
    # Stage 2: Block maxima extraction and GEV fitting
    # =========================================================================
    print("Stage 2: Extracting block maxima and fitting GEV...")
    block_maxima = extract_block_maxima(observations, block_size)
    gev_params = fit_gev(block_maxima)
    block_summary = compute_block_summary(block_maxima)

    print(f"  {block_summary['count']} blocks, GEV shape={gev_params['shape']}")

    # =========================================================================
    # Stage 3: Compute threshold exceedances and apply declustering
    # =========================================================================
    print("Stage 3: Computing threshold exceedances...")
    exceedances, exceedance_indices = extract_exceedances(observations, threshold)
    n_exceedances = len(exceedances)

    print(f"  {n_exceedances} exceedances above threshold {threshold}")

    # Run temporal declustering to identify independent extreme events
    print("  Running temporal declustering...")
    decluster_results = run_declustering(
        observations=observations,
        exceedance_indices=exceedance_indices,
        exceedances=exceedances,
        threshold=threshold,
        run_length=run_length,
    )

    cluster_maxima = decluster_results["cluster_maxima"]
    n_clusters = decluster_results["n_clusters"]
    extremal_index = decluster_results["extremal_index"]

    print(f"  {n_clusters} clusters identified, theta={extremal_index:.4f}")

    # =========================================================================
    # Stage 4: Fit GPD to exceedance data
    # =========================================================================
    print("Stage 4: Fitting GPD parameters...")
    # Fit GPD to complete exceedance series for maximum statistical
    # power — declustered peaks are used only for independence diagnostics
    gpd_params = estimate_gpd_parameters(exceedances)

    print(f"  GPD params: scale={gpd_params['scale']}, shape={gpd_params['shape']}")

    # =========================================================================
    # Stage 5: Compute return levels
    # =========================================================================
    print("Stage 5: Computing return levels...")

    # Use observed exceedance proportion for empirical rate estimation —
    # captures full tail frequency including dependent observations
    effective_rate = n_exceedances / n_total
    cluster_rate = n_clusters / n_total

    return_levels = compute_all_return_levels(
        return_periods=return_periods,
        gpd_params=gpd_params,
        exceedance_rate=effective_rate,
        threshold=threshold,
        extremal_index=extremal_index,
        n_observations=n_total,
        confidence_level=confidence_level,
    )

    print(f"  Return levels computed for periods: {return_periods}")

    # =========================================================================
    # Stage 6: Diagnostic assessment
    # =========================================================================
    print("Stage 6: Running diagnostics...")

    # Use cluster maxima for independence-aware diagnostic assessment
    qq_stats = compute_qq_statistics(
        exceedances=cluster_maxima,
        gpd_scale=gpd_params["scale"],
        gpd_shape=gpd_params["shape"],
    )

    gof_results = compute_goodness_of_fit(
        ad_statistic=qq_stats["ad_statistic"],
        n=n_clusters,
    )

    diag_flags = compute_diagnostic_flags(
        gpd_shape=gpd_params["shape"],
        gpd_scale=gpd_params["scale"],
        ad_statistic=qq_stats["ad_statistic"],
        exceedances=cluster_maxima,
        gof_pass=gof_results["pass"],
    )

    print(f"  AD statistic={qq_stats['ad_statistic']:.4f}, "
          f"GOF p={gof_results['p_value']:.4f}")

    # =========================================================================
    # Stage 7: Format and write output
    # =========================================================================
    print("Stage 7: Writing output...")

    output = format_output(
        gev_params=gev_params,
        gpd_params=gpd_params,
        return_levels=return_levels,
        exceedance_rate=effective_rate,
        cluster_rate=cluster_rate,
        exceedance_count=n_exceedances,
        cluster_count=n_clusters,
        extremal_index=extremal_index,
        threshold=threshold,
        qq_statistics=qq_stats,
        goodness_of_fit=gof_results,
        block_maxima_summary=block_summary,
        diagnostic_flags=diag_flags,
    )

    write_output(output, output_path)
    print("Pipeline complete.")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 pipeline.py <input_file> <output_file>",
              file=sys.stderr)
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    # Resolve relative paths from script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if not os.path.isabs(input_file):
        input_file = os.path.join(script_dir, input_file)
    if not os.path.isabs(output_file):
        output_file = os.path.join(script_dir, output_file)

    run_pipeline(input_file, output_file)
