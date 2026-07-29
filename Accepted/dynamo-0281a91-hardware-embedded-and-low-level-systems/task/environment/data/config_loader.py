"""Device configuration loader for embedded sensor fusion platform."""
import json
import os


def load_config(config_path):
    """Load and validate device configuration from JSON file."""
    with open(config_path, 'r') as f:
        config = json.load(f)
    
    required_sections = ['sensors', 'calibration', 'fusion', 'control', 'telemetry']
    for section in required_sections:
        if section not in config:
            raise ValueError(f"Missing required config section: {section}")
    
    return config


def get_sensor_config(config):
    """Extract sensor configuration parameters."""
    sensors = config['sensors']
    return {
        'sample_rate_hz': sensors.get('sample_rate_hz', 100),
        'accel_range_g': sensors.get('accel_range_g', 16),
        'gyro_range_dps': sensors.get('gyro_range_dps', 2000),
        'mag_range_ut': sensors.get('mag_range_ut', 4800),
        'temp_range_c': sensors.get('temp_range_c', [-40, 125]),
    }


def get_calibration_config(config):
    """Extract calibration matrices and bias vectors."""
    cal = config['calibration']
    return {
        'accel': {
            'matrix': cal.get('accel_matrix', [[1,0,0],[0,1,0],[0,0,1]]),
            'bias': cal.get('accel_bias', [0.0, 0.0, 0.0])
        },
        'gyro': {
            'matrix': cal.get('gyro_matrix', [[1,0,0],[0,1,0],[0,0,1]]),
            'bias': cal.get('gyro_bias', [0.0, 0.0, 0.0])
        },
        'mag': {
            'matrix': cal.get('mag_matrix', [[1,0,0],[0,1,0],[0,0,1]]),
            'bias': cal.get('mag_bias', [0.0, 0.0, 0.0])
        }
    }


def get_fusion_config(config):
    """Extract sensor fusion parameters."""
    fusion = config['fusion']
    return {
        'complementary_alpha': fusion.get('complementary_alpha', 0.98),
        'mag_declination_deg': fusion.get('mag_declination_deg', 0.0),
        'initial_orientation': fusion.get('initial_orientation', [1.0, 0.0, 0.0, 0.0]),
    }


def get_control_config(config):
    """Extract PID control parameters."""
    ctrl = config['control']
    return {
        'kp': ctrl.get('kp', 1.0),
        'ki': ctrl.get('ki', 0.1),
        'kd': ctrl.get('kd', 0.05),
        'setpoint': ctrl.get('setpoint', [0.0, 0.0, 0.0]),
        'output_limit': ctrl.get('output_limit', 1.0),
        'integral_limit': ctrl.get('integral_limit', 0.5),
        'dt': 1.0 / config['sensors'].get('sample_rate_hz', 100),
    }


def get_telemetry_config(config):
    """Extract telemetry output parameters."""
    tel = config['telemetry']
    return {
        'include_raw': tel.get('include_raw_sensors', False),
        'include_calibrated': tel.get('include_calibrated', True),
        'quaternion_format': tel.get('quaternion_format', 'wxyz'),
        'decimal_precision': tel.get('decimal_precision', 6),
    }
