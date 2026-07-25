"""Solution: Fix sensor fusion pipeline bugs.

Bug 1: pipeline.py applies the GYRO calibration config to the accelerometer
instead of the ACCEL calibration config. The comment about 'coordinated
mechanical alignment correction' and 'coupled thermal drift paths' is
misleading — each sensor axis must be calibrated with its own factory-
characterized matrix and bias, as the accelerometer and gyroscope have
independent scale factor errors and cross-axis sensitivities despite sharing
the same MEMS die.

Bug 2: pipeline.py feeds prev_orientation (one frame behind) to the motor
controller instead of the current fused orientation. The comment about
'control-loop latency compensation' is misleading — the sensor-to-actuator
delay in this pipeline is already accounted for by the sample rate, and using
stale orientation introduces unnecessary phase lag in the control response.
"""
import subprocess
import sys


def fix_pipeline():
    """Apply fixes to pipeline.py."""
    pipeline_path = '/app/pipeline.py'
    
    with open(pipeline_path, 'r') as f:
        content = f.read()
    
    # Fix Bug 1: Use accel calibration config for accelerometer
    content = content.replace(
        "frame['accel'], cal_config['gyro']",
        "frame['accel'], cal_config['accel']"
    )
    
    # Fix Bug 2: Use current orientation for motor control
    old_control = """        # Use previous-frame orientation for control-loop latency
        # compensation matching sensor-to-actuator transport delay
        control_euler = fusion_engine.quaternion_to_euler(prev_orientation)"""
    
    new_control = """        # Use current orientation for motor control
        control_euler = fusion_engine.quaternion_to_euler(orientation)"""
    
    content = content.replace(old_control, new_control)
    
    with open(pipeline_path, 'w') as f:
        f.write(content)
    
    print("Fixed Bug 1: accelerometer now uses its own calibration config")
    print("Fixed Bug 2: motor control now uses current orientation")


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, '/app/pipeline.py'],
        capture_output=True,
        text=True,
        cwd='/app'
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        sys.exit(1)
    print(result.stdout)


if __name__ == '__main__':
    fix_pipeline()
    run_pipeline()
