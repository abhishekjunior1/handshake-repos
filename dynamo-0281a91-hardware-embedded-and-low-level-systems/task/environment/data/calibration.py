"""Sensor calibration module for bias removal and cross-axis correction.

Applies factory-calibrated correction matrices and bias vectors
to raw sensor readings. The calibration model is:

    calibrated = matrix @ (raw - bias)

This corrects for:
- Zero-rate offset (bias)
- Scale factor errors (diagonal of matrix)
- Cross-axis sensitivity (off-diagonal of matrix)
"""
import math


def apply_calibration(raw_reading, cal_params):
    """Apply calibration matrix and bias correction to a 3-axis sensor reading.
    
    Args:
        raw_reading: [x, y, z] raw sensor values
        cal_params: dict with 'matrix' (3x3) and 'bias' (3-vector)
    
    Returns:
        [x, y, z] calibrated values
    """
    matrix = cal_params['matrix']
    bias = cal_params['bias']
    
    # Remove bias first
    debiased = [raw_reading[i] - bias[i] for i in range(3)]
    
    # Apply correction matrix
    calibrated = matrix_vector_multiply(matrix, debiased)
    
    return calibrated


def matrix_vector_multiply(matrix, vector):
    """Multiply 3x3 matrix by 3-vector."""
    result = [0.0, 0.0, 0.0]
    for i in range(3):
        for j in range(3):
            result[i] += matrix[i][j] * vector[j]
    return result


def calibrate_all_sensors(frame, cal_config):
    """Apply calibration to all sensors in a frame.
    
    Args:
        frame: dict with 'accel', 'gyro', 'mag' raw readings
        cal_config: dict with 'accel', 'gyro', 'mag' calibration params
    
    Returns:
        dict with calibrated sensor readings
    """
    calibrated = {}
    
    calibrated['accel'] = apply_calibration(frame['accel'], cal_config['accel'])
    calibrated['gyro'] = apply_calibration(frame['gyro'], cal_config['gyro'])
    
    if frame.get('mag') is not None:
        calibrated['mag'] = apply_calibration(frame['mag'], cal_config['mag'])
    else:
        calibrated['mag'] = None
    
    calibrated['temp_c'] = frame.get('temp_c')
    calibrated['timestamp_us'] = frame['timestamp_us']
    
    return calibrated


def compute_calibration_residuals(raw_frames, cal_config, reference_gravity=9.81):
    """Compute calibration quality metrics.
    
    For a stationary sensor, the calibrated accelerometer magnitude
    should be close to 1g. Deviation indicates calibration error.
    """
    residuals = []
    for frame in raw_frames:
        cal = apply_calibration(frame['accel'], cal_config['accel'])
        mag = math.sqrt(sum(v**2 for v in cal))
        residuals.append(abs(mag - reference_gravity))
    
    if not residuals:
        return {'mean_residual': 0.0, 'max_residual': 0.0}
    
    return {
        'mean_residual': sum(residuals) / len(residuals),
        'max_residual': max(residuals),
    }


def apply_temperature_compensation(cal_params, temp_c, temp_coefficients=None):
    """Adjust calibration for temperature drift.
    
    Temperature compensation applies a linear correction to bias:
        adjusted_bias = bias + temp_coeff * (temp - 25.0)
    """
    if temp_coefficients is None or temp_c is None:
        return cal_params
    
    ref_temp = 25.0
    delta_t = temp_c - ref_temp
    
    adjusted_bias = [
        cal_params['bias'][i] + temp_coefficients[i] * delta_t
        for i in range(3)
    ]
    
    return {
        'matrix': cal_params['matrix'],
        'bias': adjusted_bias
    }


def validate_calibration_matrix(matrix):
    """Check that calibration matrix is well-conditioned.
    
    A valid calibration matrix should have:
    - Diagonal elements close to 1.0 (scale factors)
    - Off-diagonal elements small (cross-axis < 5%)
    - Positive determinant (no axis flips)
    """
    for i in range(3):
        if abs(matrix[i][i] - 1.0) > 0.15:
            return False, f"Scale factor axis {i} out of range: {matrix[i][i]}"
    
    for i in range(3):
        for j in range(3):
            if i != j and abs(matrix[i][j]) > 0.05:
                return False, f"Cross-axis [{i}][{j}] too large: {matrix[i][j]}"
    
    # Compute determinant (3x3)
    det = (matrix[0][0] * (matrix[1][1] * matrix[2][2] - matrix[1][2] * matrix[2][1])
           - matrix[0][1] * (matrix[1][0] * matrix[2][2] - matrix[1][2] * matrix[2][0])
           + matrix[0][2] * (matrix[1][0] * matrix[2][1] - matrix[1][1] * matrix[2][0]))
    
    if det <= 0:
        return False, f"Non-positive determinant: {det}"
    
    return True, "OK"
