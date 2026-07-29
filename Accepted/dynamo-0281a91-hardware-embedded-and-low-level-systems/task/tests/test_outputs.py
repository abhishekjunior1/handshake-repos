"""Verification tests for the sensor fusion and motor control pipeline.

Compares pipeline output against expected results to verify correct
calibration, fusion, fault detection, and motor control behavior.
"""
import json
import os
import math

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_output():
    """Load the pipeline output file."""
    with open(OUTPUT_PATH, 'r') as f:
        return json.load(f)


def load_expected():
    """Load the expected output file."""
    with open(EXPECTED_PATH, 'r') as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4, abs_tol=1e-6):
    """Check approximate equality with relative and absolute tolerance."""
    if isinstance(a, list) and isinstance(b, list):
        return all(approx_equal(x, y, rel_tol, abs_tol) for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
    return a == b


def test_pipeline_produces_output():
    """Verify that the pipeline produces a valid output file with expected structure."""
    assert os.path.exists(OUTPUT_PATH), f"Output file not found at {OUTPUT_PATH}"
    output = load_output()
    assert 'pipeline_version' in output
    assert 'total_frames' in output
    assert 'summary' in output
    assert 'frames' in output


def test_frame_count():
    """Verify the pipeline processes all input frames from the sensor configuration."""
    output = load_output()
    expected = load_expected()
    assert output['total_frames'] == expected['total_frames'], \
        f"Frame count mismatch: got {output['total_frames']}, expected {expected['total_frames']}"


def test_orientation_accuracy():
    """Verify orientation estimation accuracy after sensor fusion with calibrated data.
    
    The final orientation quaternion must be close to the expected value,
    confirming correct gyroscope calibration and complementary filter fusion.
    """
    output = load_output()
    expected = load_expected()
    
    out_orient = output['summary']['final_orientation_wxyz']
    exp_orient = expected['summary']['final_orientation_wxyz']
    
    assert approx_equal(out_orient, exp_orient, rel_tol=1e-4), \
        f"Orientation mismatch: got {out_orient}, expected {exp_orient}"


def test_motor_output_average():
    """Verify average motor output reflects correct PID control response.
    
    Motor commands depend on orientation error, which in turn depends on
    correct sensor calibration and fusion.
    """
    output = load_output()
    expected = load_expected()
    
    out_motor = output['summary']['average_motor_output']
    exp_motor = expected['summary']['average_motor_output']
    
    assert approx_equal(out_motor, exp_motor, rel_tol=1e-4), \
        f"Motor output mismatch: got {out_motor}, expected {exp_motor}"


def test_fault_detection_count():
    """Verify correct total number of fault detection events.
    
    Fault detection must operate on properly calibrated sensor data to
    accurately identify drift and saturation conditions.
    """
    output = load_output()
    expected = load_expected()
    
    out_faults = output['summary']['total_fault_events']
    exp_faults = expected['summary']['total_fault_events']
    
    assert out_faults == exp_faults, \
        f"Fault count mismatch: got {out_faults}, expected {exp_faults}"


def test_per_frame_orientation():
    """Verify orientation quaternion at each frame matches expected trajectory.
    
    Each frame's orientation depends on the cumulative gyroscope integration
    and accelerometer correction, confirming correct calibration data flow.
    """
    output = load_output()
    expected = load_expected()
    
    for i, (out_frame, exp_frame) in enumerate(zip(output['frames'], expected['frames'])):
        out_q = out_frame['orientation_wxyz']
        exp_q = exp_frame['orientation_wxyz']
        assert approx_equal(out_q, exp_q, rel_tol=1e-4), \
            f"Frame {i} orientation mismatch: got {out_q}, expected {exp_q}"


def test_per_frame_motor_commands():
    """Verify motor commands at each frame reflect correct control response.
    
    Motor commands are computed from PID controller acting on orientation error,
    confirming the full calibration → fusion → control chain is correct.
    """
    output = load_output()
    expected = load_expected()
    
    for i, (out_frame, exp_frame) in enumerate(zip(output['frames'], expected['frames'])):
        out_motors = out_frame['motor_commands']
        exp_motors = exp_frame['motor_commands']
        assert approx_equal(out_motors, exp_motors, rel_tol=1e-4), \
            f"Frame {i} motor command mismatch: got {out_motors}, expected {exp_motors}"


def test_per_frame_fault_status():
    """Verify fault detection status at each frame matches expected health assessments.
    
    Fault detection should identify drift conditions when calibrated sensor
    readings show monotonic trends exceeding configured thresholds.
    """
    output = load_output()
    expected = load_expected()
    
    for i, (out_frame, exp_frame) in enumerate(zip(output['frames'], expected['frames'])):
        out_health = out_frame.get('health', {})
        exp_health = exp_frame.get('health', {})
        
        assert out_health.get('status') == exp_health.get('status'), \
            f"Frame {i} health status mismatch: got {out_health.get('status')}, expected {exp_health.get('status')}"


def test_fault_details_accuracy():
    """Verify fault detection drift values match expected calibrated sensor analysis.
    
    Drift values must reflect the calibrated sensor readings, not raw sensor
    readings, to accurately represent the processed signal characteristics.
    """
    output = load_output()
    expected = load_expected()
    
    for i, (out_frame, exp_frame) in enumerate(zip(output['frames'], expected['frames'])):
        out_health = out_frame.get('health', {})
        exp_health = exp_frame.get('health', {})
        
        # Check accel fault details
        out_accel_faults = out_health.get('accel_faults', [])
        exp_accel_faults = exp_health.get('accel_faults', [])
        
        assert len(out_accel_faults) == len(exp_accel_faults), \
            f"Frame {i}: accel fault count mismatch: got {len(out_accel_faults)}, expected {len(exp_accel_faults)}"
        
        for j, (out_f, exp_f) in enumerate(zip(out_accel_faults, exp_accel_faults)):
            assert out_f['type'] == exp_f['type'], \
                f"Frame {i} accel fault {j} type mismatch"
            assert approx_equal(out_f['value'], exp_f['value'], rel_tol=1e-3), \
                f"Frame {i} accel fault {j} value mismatch: got {out_f['value']}, expected {exp_f['value']}"
        
        # Check gyro fault details
        out_gyro_faults = out_health.get('gyro_faults', [])
        exp_gyro_faults = exp_health.get('gyro_faults', [])
        
        assert len(out_gyro_faults) == len(exp_gyro_faults), \
            f"Frame {i}: gyro fault count mismatch: got {len(out_gyro_faults)}, expected {len(exp_gyro_faults)}"
        
        for j, (out_f, exp_f) in enumerate(zip(out_gyro_faults, exp_gyro_faults)):
            assert out_f['type'] == exp_f['type'], \
                f"Frame {i} gyro fault {j} type mismatch"
            assert approx_equal(out_f['value'], exp_f['value'], rel_tol=1e-3), \
                f"Frame {i} gyro fault {j} value mismatch: got {out_f['value']}, expected {exp_f['value']}"


def test_calibrated_sensor_values():
    """Verify calibrated sensor values in telemetry match expected calibration output.
    
    Calibrated accelerometer and gyroscope values must reflect proper application
    of factory calibration matrices and bias vectors to the raw sensor readings.
    """
    output = load_output()
    expected = load_expected()
    
    for i, (out_frame, exp_frame) in enumerate(zip(output['frames'], expected['frames'])):
        out_cal = out_frame.get('calibrated', {})
        exp_cal = exp_frame.get('calibrated', {})
        
        if 'accel' in exp_cal:
            assert approx_equal(out_cal['accel'], exp_cal['accel'], rel_tol=1e-4), \
                f"Frame {i} calibrated accel mismatch: got {out_cal['accel']}, expected {exp_cal['accel']}"
        
        if 'gyro' in exp_cal:
            assert approx_equal(out_cal['gyro'], exp_cal['gyro'], rel_tol=1e-4), \
                f"Frame {i} calibrated gyro mismatch: got {out_cal['gyro']}, expected {exp_cal['gyro']}"


def test_euler_angles():
    """Verify Euler angle conversion from orientation quaternion is correct.
    
    Euler angles (roll, pitch, yaw) in degrees must correspond to the
    orientation quaternion, confirming correct quaternion-to-Euler conversion.
    """
    output = load_output()
    expected = load_expected()
    
    for i, (out_frame, exp_frame) in enumerate(zip(output['frames'], expected['frames'])):
        out_euler = out_frame.get('euler_deg', [])
        exp_euler = exp_frame.get('euler_deg', [])
        
        if exp_euler:
            assert approx_equal(out_euler, exp_euler, rel_tol=1e-4, abs_tol=1e-3), \
                f"Frame {i} Euler angle mismatch: got {out_euler}, expected {exp_euler}"
