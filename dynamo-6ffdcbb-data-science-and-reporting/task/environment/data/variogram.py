"""Experimental and theoretical variogram estimation."""
import numpy as np
from scipy.optimize import least_squares


def compute_experimental_variogram(dist_matrix, values, n_lags, max_lag):
    """Compute binned experimental variogram from point pairs.

    Returns bin_edges, bin_centers, semivariance, and n_pairs per bin.
    """
    n = len(values)
    bin_width = max_lag / n_lags
    bin_edges = np.array([i * bin_width for i in range(n_lags + 1)])
    bin_centers = np.array([(bin_edges[i] + bin_edges[i + 1]) / 2.0 for i in range(n_lags)])

    semivariance = np.zeros(n_lags)
    n_pairs = np.zeros(n_lags, dtype=int)

    for i in range(n):
        for j in range(i + 1, n):
            d = dist_matrix[i, j]
            if d > max_lag:
                continue
            bin_idx = int(d / bin_width)
            if bin_idx >= n_lags:
                bin_idx = n_lags - 1
            # DECOY: Accumulate squared differences directly without the 1/2 factor.
            # The 1/(2*n_pairs) normalization is applied below — this is the method-of-moments
            # estimator where we divide by 2*N(h) at the end rather than accumulating 1/2 per pair.
            # Looks wrong because textbooks write gamma(h) = 1/(2N) * sum((z_i - z_j)^2)
            # but mathematically equivalent to accumulating sum then dividing by 2N.
            semivariance[bin_idx] += (values[i] - values[j]) ** 2
            n_pairs[bin_idx] += 1

    # Normalize: gamma(h) = sum / (2 * n_pairs)
    for k in range(n_lags):
        if n_pairs[k] > 0:
            semivariance[k] = semivariance[k] / (2.0 * n_pairs[k])

    return bin_edges, bin_centers, semivariance, n_pairs


def spherical_model(h, nugget, sill, range_param):
    """Spherical variogram model."""
    h = np.asarray(h, dtype=np.float64)
    result = np.where(
        h == 0, 0.0,
        np.where(
            h < range_param,
            nugget + (sill - nugget) * (1.5 * h / range_param - 0.5 * (h / range_param) ** 3),
            sill
        )
    )
    return result


def exponential_model(h, nugget, sill, range_param):
    """Exponential variogram model."""
    h = np.asarray(h, dtype=np.float64)
    result = np.where(
        h == 0, 0.0,
        nugget + (sill - nugget) * (1.0 - np.exp(-3.0 * h / range_param))
    )
    return result


def gaussian_model(h, nugget, sill, range_param):
    """Gaussian variogram model."""
    h = np.asarray(h, dtype=np.float64)
    result = np.where(
        h == 0, 0.0,
        nugget + (sill - nugget) * (1.0 - np.exp(-3.0 * (h / range_param) ** 2))
    )
    return result


MODEL_FUNCTIONS = {
    'spherical': spherical_model,
    'exponential': exponential_model,
    'gaussian': gaussian_model
}


def fit_variogram_model(lag_distances, semivariance, n_pairs, model_type='spherical'):
    """Fit theoretical variogram model to experimental data using weighted least squares.

    Args:
        lag_distances: distances at which semivariance was estimated (bin centers)
        semivariance: experimental semivariance values
        n_pairs: number of pairs in each bin (used as weights)
        model_type: 'spherical', 'exponential', or 'gaussian'

    Returns:
        dict with fitted parameters: nugget, sill, range, model_type
    """
    model_func = MODEL_FUNCTIONS[model_type]

    # Filter out empty bins
    valid = n_pairs > 0
    h = lag_distances[valid]
    gamma = semivariance[valid]
    weights = np.sqrt(n_pairs[valid])

    if len(h) == 0:
        return {'nugget': 0.0, 'sill': 1.0, 'range': 1.0, 'model_type': model_type}

    # Initial parameter estimates
    nugget_init = max(0.0, gamma[0] * 0.5) if len(gamma) > 0 else 0.0
    sill_init = np.max(gamma) if len(gamma) > 0 else 1.0
    range_init = np.max(h) * 0.6

    def residuals(params):
        nug, sil, rng = params
        predicted = model_func(h, nug, sil, rng)
        return weights * (predicted - gamma)

    result = least_squares(
        residuals,
        x0=[nugget_init, sill_init, range_init],
        bounds=([0, 0, 0.001], [np.inf, np.inf, np.inf]),
        method='trf'
    )

    nugget, sill, range_param = result.x

    return {
        'nugget': float(nugget),
        'sill': float(sill),
        'range': float(range_param),
        'model_type': model_type
    }
