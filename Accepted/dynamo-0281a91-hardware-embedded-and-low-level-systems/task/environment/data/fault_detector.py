"""Sensor fault detection module for embedded health monitoring.

Detects common sensor failure modes:
- Stuck sensor (constant reading over time window)
- Drift (monotonic trend beyond threshold)
- Saturation (reading at sensor limits)
- Noise floor violation (variance too low = dead sensor)

Requires a HISTORY of calibrated sensor readings to detect temporal faults.
With insufficient history, all sensors report as healthy.
"""
import math


def detect_faults(sensor_history, sensor_config, thresholds=None):
    """Run fault detection on sensor history.
    
    Args:
        sensor_history: list of calibrated sensor readings (dicts with 'accel', 'gyro', etc.)
            Must contain at least 5 samples for meaningful fault detection.
        sensor_config: sensor range/configuration parameters
        thresholds: optional custom fault thresholds
    
    Returns:
        dict with fault status per sensor axis
    """
    if thresholds is None:
        thresholds = get_default_thresholds()
    
    min_history = thresholds.get('min_history_samples', 5)
    
    if len(sensor_history) < min_history:
        return {
            'status': 'healthy',
            'accel_faults': [],
            'gyro_faults': [],
            'mag_faults': [],
            'details': 'Insufficient history for fault detection'
        }
    
    accel_faults = check_sensor_faults(
        [s['accel'] for s in sensor_history],
        'accel',
        sensor_config['accel_range_g'] * 9.81,
        thresholds
    )
    
    gyro_faults = check_sensor_faults(
        [s['gyro'] for s in sensor_history],
        'gyro',
        math.radians(sensor_config['gyro_range_dps']),
        thresholds
    )
    
    mag_faults = []
    mag_readings = [s.get('mag') for s in sensor_history if s.get('mag') is not None]
    if len(mag_readings) >= min_history:
        mag_faults = check_sensor_faults(
            mag_readings,
            'mag',
            sensor_config['mag_range_ut'],
            thresholds
        )
    
    all_faults = accel_faults + gyro_faults + mag_faults
    status = 'fault_detected' if all_faults else 'healthy'
    
    return {
        'status': status,
        'accel_faults': accel_faults,
        'gyro_faults': gyro_faults,
        'mag_faults': mag_faults,
        'details': format_fault_summary(all_faults) if all_faults else 'All sensors nominal'
    }


def check_sensor_faults(readings, sensor_name, max_range, thresholds):
    """Check a single sensor type for faults across all axes."""
    faults = []
    axis_names = ['x', 'y', 'z']
    
    for axis in range(3):
        axis_values = [r[axis] for r in readings]
        
        # Check for stuck sensor
        if is_stuck(axis_values, thresholds['stuck_tolerance']):
            faults.append({
                'sensor': sensor_name,
                'axis': axis_names[axis],
                'type': 'stuck',
                'value': axis_values[-1]
            })
        
        # Check for saturation
        if is_saturated(axis_values, max_range, thresholds['saturation_margin']):
            faults.append({
                'sensor': sensor_name,
                'axis': axis_names[axis],
                'type': 'saturated',
                'value': axis_values[-1]
            })
        
        # Check for drift
        if has_monotonic_drift(axis_values, thresholds['drift_threshold']):
            faults.append({
                'sensor': sensor_name,
                'axis': axis_names[axis],
                'type': 'drift',
                'value': axis_values[-1] - axis_values[0]
            })
    
    return faults


def is_stuck(values, tolerance):
    """Detect stuck sensor: all values within tolerance of each other."""
    if len(values) < 3:
        return False
    min_val = min(values)
    max_val = max(values)
    return (max_val - min_val) < tolerance


def is_saturated(values, max_range, margin):
    """Detect saturated sensor: values consistently near range limits."""
    threshold = max_range * (1.0 - margin)
    saturated_count = sum(1 for v in values if abs(v) > threshold)
    return saturated_count > len(values) * 0.8


def has_monotonic_drift(values, threshold):
    """Detect monotonic drift: consistent trend in one direction."""
    if len(values) < 5:
        return False
    
    diffs = [values[i+1] - values[i] for i in range(len(values)-1)]
    positive_diffs = sum(1 for d in diffs if d > 0)
    negative_diffs = sum(1 for d in diffs if d < 0)
    
    total_drift = abs(values[-1] - values[0])
    
    if total_drift < threshold:
        return False
    
    # Monotonic if 90%+ of differences are in same direction
    n = len(diffs)
    return positive_diffs > n * 0.9 or negative_diffs > n * 0.9


def get_default_thresholds():
    """Return default fault detection thresholds."""
    return {
        'min_history_samples': 5,
        'stuck_tolerance': 0.001,
        'saturation_margin': 0.05,
        'drift_threshold': 0.5,
    }


def format_fault_summary(faults):
    """Format fault list into human-readable summary."""
    if not faults:
        return 'No faults detected'
    
    summaries = []
    for fault in faults:
        summaries.append(
            f"{fault['sensor']}.{fault['axis']}: {fault['type']} (value={fault['value']:.4f})"
        )
    return '; '.join(summaries)
