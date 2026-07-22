"""Telemetry frame packaging for embedded data output.

Formats sensor fusion results into structured output frames
for downstream logging, communication, and analysis.

Quaternion output uses WXYZ ordering (scalar-first) which is the
standard convention for aerospace and robotics firmware.
"""


def package_telemetry_frame(frame_data, telemetry_config, frame_index):
    """Package a single telemetry output frame.
    
    Args:
        frame_data: dict with orientation, control, faults, etc.
        telemetry_config: output format configuration
        frame_index: sequential frame counter
    
    Returns:
        Formatted telemetry frame dict
    """
    precision = telemetry_config.get('decimal_precision', 6)
    
    frame = {
        'frame_id': frame_index,
        'timestamp_us': frame_data['timestamp_us'],
    }
    
    # Orientation quaternion in WXYZ format (scalar-first)
    if 'orientation' in frame_data:
        q = frame_data['orientation']
        frame['orientation_wxyz'] = round_vector(q, precision)
    
    # Euler angles for human readability
    if 'euler_angles' in frame_data:
        frame['euler_deg'] = round_vector(
            [v * 57.29577951308232 for v in frame_data['euler_angles']],
            precision
        )
    
    # Motor commands
    if 'motor_commands' in frame_data:
        frame['motor_commands'] = round_vector(frame_data['motor_commands'], precision)
    
    # Control diagnostics
    if 'control_diagnostics' in frame_data:
        frame['control'] = round_dict(frame_data['control_diagnostics'], precision)
    
    # Include raw sensor data if configured
    if telemetry_config.get('include_raw_sensors', False) and 'raw' in frame_data:
        frame['raw_sensors'] = {
            'accel': round_vector(frame_data['raw']['accel'], precision),
            'gyro': round_vector(frame_data['raw']['gyro'], precision),
        }
    
    # Include calibrated data if configured  
    if telemetry_config.get('include_calibrated', True) and 'calibrated' in frame_data:
        frame['calibrated'] = {
            'accel': round_vector(frame_data['calibrated']['accel'], precision),
            'gyro': round_vector(frame_data['calibrated']['gyro'], precision),
        }
    
    # Fault status
    if 'fault_status' in frame_data:
        frame['health'] = frame_data['fault_status']
    
    return frame


def package_output(frames, summary, telemetry_config):
    """Package complete telemetry output with summary."""
    precision = telemetry_config.get('decimal_precision', 6)
    
    output = {
        'pipeline_version': '1.0.0',
        'total_frames': len(frames),
        'summary': round_dict(summary, precision) if summary else {},
        'frames': frames,
    }
    
    return output


def compute_output_summary(all_frame_data):
    """Compute summary statistics over all processed frames."""
    if not all_frame_data:
        return {}
    
    n = len(all_frame_data)
    
    # Average orientation (last quaternion as representative)
    final_orientation = all_frame_data[-1].get('orientation', [1,0,0,0])
    
    # Average motor command magnitude
    motor_mags = []
    for fd in all_frame_data:
        if 'motor_commands' in fd:
            motors = fd['motor_commands']
            motor_mags.append(sum(motors) / len(motors))
    
    avg_motor = sum(motor_mags) / len(motor_mags) if motor_mags else 0.0
    
    # Fault count
    fault_count = sum(
        1 for fd in all_frame_data
        if fd.get('fault_status', {}).get('status') == 'fault_detected'
    )
    
    return {
        'final_orientation_wxyz': final_orientation,
        'average_motor_output': avg_motor,
        'total_fault_events': fault_count,
        'frames_processed': n,
    }


def round_vector(vec, precision):
    """Round all elements of a vector to given decimal precision."""
    return [round(v, precision) for v in vec]


def round_dict(d, precision):
    """Round all numeric values in a dict to given precision."""
    result = {}
    for k, v in d.items():
        if isinstance(v, float):
            result[k] = round(v, precision)
        elif isinstance(v, list):
            result[k] = round_vector(v, precision)
        else:
            result[k] = v
    return result
