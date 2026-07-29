"""Spatial data loader for geostatistical pipeline."""
import json
import sys
import numpy as np


def load_config(path):
    """Load spatial dataset and pipeline configuration."""
    try:
        with open(path, 'r') as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading config: {e}", file=sys.stderr)
        sys.exit(1)
    for key in ['points', 'variogram_settings', 'kriging_settings']:
        if key not in config:
            print(f"Missing config section: {key}", file=sys.stderr)
            sys.exit(1)
    return config


def extract_points(config):
    """Extract spatial coordinates and measured values."""
    pts = config['points']
    x = np.array(pts['x'], dtype=np.float64)
    y = np.array(pts['y'], dtype=np.float64)
    z = np.array(pts['z'], dtype=np.float64)
    if not (len(x) == len(y) == len(z)):
        print("Point arrays must have equal length", file=sys.stderr)
        sys.exit(1)
    coords = np.column_stack([x, y])
    return coords, z


def extract_variogram_settings(config):
    """Extract variogram estimation settings."""
    vs = config['variogram_settings']
    return {
        'n_lags': vs.get('n_lags', 10),
        'max_lag': vs.get('max_lag', None),
        'model_type': vs.get('model_type', 'spherical')
    }


def extract_kriging_settings(config):
    """Extract kriging interpolation settings."""
    ks = config['kriging_settings']
    return {
        'prediction_points': np.array(ks['prediction_points'], dtype=np.float64) if 'prediction_points' in ks else None,
        'use_cross_validation': ks.get('use_cross_validation', True)
    }


def compute_distance_matrix(coords):
    """Compute pairwise Euclidean distance matrix."""
    n = len(coords)
    dists = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            d = np.sqrt(np.sum((coords[i] - coords[j]) ** 2))
            dists[i, j] = d
            dists[j, i] = d
    return dists


def prepare_inputs(config_path):
    """Load config and prepare all pipeline inputs."""
    config = load_config(config_path)
    coords, values = extract_points(config)
    vario_settings = extract_variogram_settings(config)
    krig_settings = extract_kriging_settings(config)
    dist_matrix = compute_distance_matrix(coords)
    if vario_settings['max_lag'] is None:
        vario_settings['max_lag'] = np.max(dist_matrix) / 2.0
    return coords, values, dist_matrix, vario_settings, krig_settings
