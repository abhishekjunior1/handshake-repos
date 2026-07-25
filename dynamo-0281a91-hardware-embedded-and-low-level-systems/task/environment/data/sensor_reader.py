"""Raw sensor frame reader and validator for multi-sensor embedded platform."""
import math


def read_sensor_frames(raw_data, sensor_config):
    """Parse raw sensor data into structured frames.
    
    Each frame contains synchronized readings from all sensors
    at a single timestamp.
    """
    frames = []
    for entry in raw_data:
        frame = parse_single_frame(entry, sensor_config)
        if frame is not None:
            frames.append(frame)
    return frames


def parse_single_frame(entry, sensor_config):
    """Parse and validate a single sensor frame."""
    required_fields = ['timestamp_us', 'accel', 'gyro']
    for field in required_fields:
        if field not in entry:
            return None
    
    frame = {
        'timestamp_us': entry['timestamp_us'],
        'accel': validate_accel(entry['accel'], sensor_config),
        'gyro': validate_gyro(entry['gyro'], sensor_config),
        'mag': validate_mag(entry.get('mag'), sensor_config),
        'temp_c': validate_temp(entry.get('temp_c'), sensor_config),
    }
    
    if frame['accel'] is None or frame['gyro'] is None:
        return None
    
    return frame


def validate_accel(accel_data, sensor_config):
    """Validate accelerometer reading against configured range."""
    if accel_data is None or len(accel_data) != 3:
        return None
    
    max_val = sensor_config['accel_range_g'] * 9.81
    for val in accel_data:
        if abs(val) > max_val * 1.1:  # 10% margin for transient spikes
            return None
    
    return list(accel_data)


def validate_gyro(gyro_data, sensor_config):
    """Validate gyroscope reading against configured range."""
    if gyro_data is None or len(gyro_data) != 3:
        return None
    
    max_val = math.radians(sensor_config['gyro_range_dps'])
    for val in gyro_data:
        if abs(val) > max_val * 1.1:
            return None
    
    return list(gyro_data)


def validate_mag(mag_data, sensor_config):
    """Validate magnetometer reading. Returns None if not present."""
    if mag_data is None:
        return None
    if len(mag_data) != 3:
        return None
    
    max_val = sensor_config['mag_range_ut']
    for val in mag_data:
        if abs(val) > max_val * 1.1:
            return None
    
    return list(mag_data)


def validate_temp(temp_data, sensor_config):
    """Validate temperature reading. Returns None if not present."""
    if temp_data is None:
        return None
    
    temp_range = sensor_config['temp_range_c']
    if temp_data < temp_range[0] or temp_data > temp_range[1]:
        return None
    
    return float(temp_data)


def compute_sample_intervals(frames):
    """Compute time intervals between consecutive frames in seconds."""
    intervals = []
    for i in range(1, len(frames)):
        dt_us = frames[i]['timestamp_us'] - frames[i-1]['timestamp_us']
        dt_s = dt_us / 1_000_000.0
        intervals.append(dt_s)
    return intervals


def get_sensor_statistics(frames):
    """Compute basic statistics over all frames for diagnostics."""
    if not frames:
        return {}
    
    n = len(frames)
    accel_magnitudes = []
    gyro_magnitudes = []
    
    for frame in frames:
        accel_mag = math.sqrt(sum(v**2 for v in frame['accel']))
        gyro_mag = math.sqrt(sum(v**2 for v in frame['gyro']))
        accel_magnitudes.append(accel_mag)
        gyro_magnitudes.append(gyro_mag)
    
    return {
        'frame_count': n,
        'accel_mag_mean': sum(accel_magnitudes) / n,
        'accel_mag_max': max(accel_magnitudes),
        'gyro_mag_mean': sum(gyro_magnitudes) / n,
        'gyro_mag_max': max(gyro_magnitudes),
    }
