"""Leave-one-out cross-validation for kriging predictions."""
import numpy as np
from kriging import predict_point


def leave_one_out_cv(coords, values, dist_matrix, model_params):
    """Perform leave-one-out cross-validation.

    For each point, predicts its value using all other points
    and records the error.

    Returns:
        predictions: array of predicted values
        variances: array of kriging variances
        errors: array of (predicted - observed)
    """
    n = len(values)
    predictions = np.zeros(n)
    variances = np.zeros(n)
    errors = np.zeros(n)

    for i in range(n):
        # Use all points except i as known data
        known_idx = np.array([j for j in range(n) if j != i])

        pred, var = predict_point(
            coords, values, coords[i], dist_matrix, model_params,
            known_indices=known_idx
        )

        predictions[i] = pred
        variances[i] = var
        errors[i] = pred - values[i]

    return predictions, variances, errors


def compute_cv_statistics(errors, variances, degrees_of_freedom):
    """Compute cross-validation summary statistics.

    Args:
        errors: prediction errors (predicted - observed)
        variances: kriging variances at each point
        degrees_of_freedom: for standardized error normalization

    Returns:
        dict with RMSE, mean_error, mean_absolute_error,
        standardized_rmse, mean_standardized_error
    """
    n = len(errors)

    rmse = np.sqrt(np.mean(errors ** 2))
    mean_error = np.mean(errors)
    mae = np.mean(np.abs(errors))

    # Standardized errors: error / sqrt(variance * n/df)
    # The df correction accounts for model parameters estimated from data
    variance_correction = n / degrees_of_freedom
    standardized_errors = np.zeros(n)
    for i in range(n):
        if variances[i] > 0:
            standardized_errors[i] = errors[i] / np.sqrt(variances[i] * variance_correction)
        else:
            standardized_errors[i] = 0.0

    standardized_rmse = np.sqrt(np.mean(standardized_errors ** 2))
    mean_std_error = np.mean(standardized_errors)

    return {
        'rmse': float(rmse),
        'mean_error': float(mean_error),
        'mae': float(mae),
        'standardized_rmse': float(standardized_rmse),
        'mean_standardized_error': float(mean_std_error)
    }
