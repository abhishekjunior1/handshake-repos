"""Ordinary kriging interpolation module."""
import numpy as np
from variogram import MODEL_FUNCTIONS


def covariance_from_variogram(h, model_params):
    """Convert variogram model to covariance function.

    C(h) = sill - gamma(h) for h > 0
    C(0) = sill (total variance)

    Args:
        h: distance(s)
        model_params: dict with nugget, sill, range, model_type

    Returns:
        covariance value(s)
    """
    model_func = MODEL_FUNCTIONS[model_params['model_type']]
    sill = model_params['sill']
    gamma_h = model_func(
        h, model_params['nugget'], model_params['sill'], model_params['range']
    )
    # C(h) = sill - gamma(h)
    cov = sill - gamma_h
    return cov


def build_kriging_system(dist_matrix, model_params, indices=None):
    """Build the ordinary kriging linear system.

    Constructs the covariance matrix with Lagrange multiplier row/column
    for the unbiasedness constraint.

    DECOY: The nugget effect is added ONLY to the diagonal of the covariance
    matrix (i.e., C(0) = sill, which already includes nugget via the model).
    This looks suspicious because one might expect nugget to appear everywhere,
    but in ordinary kriging the covariance at zero distance is simply the sill
    (total variance = nugget + partial sill), and the variogram model already
    handles the nugget contribution at h>0. Adding nugget to off-diagonal
    would double-count it.

    Args:
        dist_matrix: pairwise distances between known points
        model_params: fitted variogram model parameters
        indices: subset of point indices to use (for cross-validation)

    Returns:
        K: kriging matrix (n+1 x n+1) with Lagrange constraint
    """
    if indices is not None:
        dists = dist_matrix[np.ix_(indices, indices)]
    else:
        dists = dist_matrix

    n = dists.shape[0]

    # Compute covariance matrix
    C = covariance_from_variogram(dists, model_params)

    # Build augmented system with Lagrange multiplier
    K = np.zeros((n + 1, n + 1))
    K[:n, :n] = C
    K[n, :n] = 1.0
    K[:n, n] = 1.0
    K[n, n] = 0.0

    return K


def solve_kriging_weights(K, k_vec):
    """Solve kriging system for weights.

    Args:
        K: kriging matrix (n+1 x n+1)
        k_vec: covariance vector to prediction point (n+1,)

    Returns:
        weights: kriging weights (n,)
        lagrange: Lagrange multiplier
        variance: kriging variance
    """
    try:
        solution = np.linalg.solve(K, k_vec)
    except np.linalg.LinAlgError:
        # Fallback: use pseudoinverse for singular systems
        solution = np.linalg.lstsq(K, k_vec, rcond=None)[0]

    n = len(solution) - 1
    weights = solution[:n]
    lagrange = solution[n]

    # Kriging variance = C(0) - sum(w_i * C(x_i, x_0)) - lagrange
    sill = k_vec[:-1].max() if len(k_vec) > 1 else 1.0
    variance = sill - np.dot(weights, k_vec[:n]) - lagrange

    return weights, lagrange, max(0.0, variance)


def predict_point(coords, values, pred_coord, dist_matrix, model_params,
                  known_indices=None):
    """Make a kriging prediction at a single point.

    Args:
        coords: all point coordinates
        values: all measured values
        pred_coord: coordinate to predict at
        dist_matrix: full distance matrix
        model_params: fitted variogram parameters
        known_indices: which points to use as known data

    Returns:
        prediction: kriged value
        variance: kriging variance
    """
    if known_indices is None:
        known_indices = np.arange(len(values))

    n = len(known_indices)

    # Build kriging system from known points
    K = build_kriging_system(dist_matrix, model_params, known_indices)

    # Compute distances from known points to prediction point
    dists_to_pred = np.array([
        np.sqrt(np.sum((coords[idx] - pred_coord) ** 2))
        for idx in known_indices
    ])

    # Covariance vector to prediction point
    k_vec = np.zeros(n + 1)
    k_vec[:n] = covariance_from_variogram(dists_to_pred, model_params)
    k_vec[n] = 1.0  # Lagrange constraint

    # Solve for weights
    weights, lagrange, variance = solve_kriging_weights(K, k_vec)

    # Prediction
    prediction = np.dot(weights, values[known_indices])

    return prediction, variance
