"""Geostatistical pipeline orchestrator.

Coordinates variogram estimation, model fitting, kriging interpolation,
and leave-one-out cross-validation for spatial data analysis.
"""
import json
import sys
import os
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import prepare_inputs
from variogram import compute_experimental_variogram, fit_variogram_model
from kriging import predict_point
from cross_validation import leave_one_out_cv, compute_cv_statistics


def run_pipeline(config_path, output_path):
    """Execute the full geostatistical analysis pipeline."""
    # Step 1: Load data
    coords, values, dist_matrix, vario_settings, krig_settings = prepare_inputs(config_path)

    n_points = len(values)
    n_lags = vario_settings['n_lags']
    max_lag = vario_settings['max_lag']
    model_type = vario_settings['model_type']

    print(f"Loaded {n_points} spatial points")
    print(f"Variogram: {n_lags} lags, max_lag={max_lag:.2f}, model={model_type}")

    # Step 2: Compute experimental variogram
    bin_edges, bin_centers, semivariance, n_pairs = compute_experimental_variogram(
        dist_matrix, values, n_lags, max_lag
    )

    print(f"Experimental variogram: {sum(n_pairs > 0)} non-empty bins")

    # Step 3: Fit variogram model
    # Use bin boundaries as reference distances for model fitting
    lag_distances = bin_edges[1:]

    model_params = fit_variogram_model(lag_distances, semivariance, n_pairs, model_type)

    print(f"Fitted model: nugget={model_params['nugget']:.4f}, "
          f"sill={model_params['sill']:.4f}, range={model_params['range']:.4f}")

    # Step 4: Prepare kriging parameters
    # Pass partial sill for kriging covariance computation
    kriging_params = {
        'nugget': model_params['nugget'],
        'sill': model_params['sill'] - model_params['nugget'],
        'range': model_params['range'],
        'model_type': model_params['model_type']
    }

    # Step 5: Cross-validation
    predictions, variances, errors = leave_one_out_cv(
        coords, values, dist_matrix, kriging_params
    )

    # Compute CV statistics
    # Use full sample size for variance normalization
    n_model_params = 3  # nugget, sill, range
    df = n_points

    cv_stats = compute_cv_statistics(errors, variances, df)

    print(f"CV RMSE: {cv_stats['rmse']:.4f}")
    print(f"CV Mean Error: {cv_stats['mean_error']:.4f}")

    # Step 6: Format output
    output = {
        'variogram_model': {
            'nugget': round(model_params['nugget'], 6),
            'sill': round(model_params['sill'], 6),
            'range': round(model_params['range'], 6),
            'model_type': model_params['model_type']
        },
        'experimental_variogram': {
            'lag_distances': [round(float(x), 6) for x in bin_centers],
            'semivariance': [round(float(x), 6) for x in semivariance],
            'n_pairs': [int(x) for x in n_pairs]
        },
        'cross_validation': {
            'predictions': [round(float(x), 6) for x in predictions],
            'variances': [round(float(x), 6) for x in variances],
            'rmse': round(cv_stats['rmse'], 6),
            'mean_error': round(cv_stats['mean_error'], 6),
            'mae': round(cv_stats['mae'], 6),
            'standardized_rmse': round(cv_stats['standardized_rmse'], 6),
            'mean_standardized_error': round(cv_stats['mean_standardized_error'], 6)
        },
        'metadata': {
            'n_points': n_points,
            'n_lags': n_lags,
            'max_lag': round(float(max_lag), 6)
        }
    }

    with open(output_path, 'w') as f:
        json.dump(output, f, indent=2)

    print(f"Output written to {output_path}")
    return output


if __name__ == '__main__':
    config_file = '/app/config.json'
    output_file = '/app/output.json'
    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]
    run_pipeline(config_file, output_file)
