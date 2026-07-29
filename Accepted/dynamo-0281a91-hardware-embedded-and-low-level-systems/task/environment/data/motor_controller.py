"""PID motor controller with anti-windup for embedded actuator control.

Implements a discrete PID controller with:
- Trapezoidal integration for the integral term
- Derivative filtering (first-order low-pass)
- Anti-windup via integral clamping
- Output saturation limiting

The trapezoidal integration method uses (error[k] + error[k-1]) * dt / 2
for each axis, providing better accuracy than rectangular integration
for the mechanical response dynamics of brushless DC motors.
"""
import math


def compute_pid_output(error, prev_error, integral, dt, pid_params):
    """Compute PID control output for 3-axis error.
    
    Args:
        error: [roll_err, pitch_err, yaw_err] in radians
        prev_error: previous error for derivative and trapezoidal integration
        integral: accumulated integral state [3-vector]
        dt: time step in seconds
        pid_params: dict with kp, ki, kd, output_limit, integral_limit
    
    Returns:
        (output, new_integral, new_prev_error) tuple
    """
    kp = pid_params['kp']
    ki = pid_params['ki']
    kd = pid_params['kd']
    output_limit = pid_params['output_limit']
    integral_limit = pid_params['integral_limit']
    
    output = [0.0, 0.0, 0.0]
    new_integral = [0.0, 0.0, 0.0]
    
    for i in range(3):
        # Proportional term
        p_term = kp * error[i]
        
        # Integral term with trapezoidal rule for mechanical response accuracy
        integral_increment = (error[i] + prev_error[i]) * dt / 2.0
        new_integral[i] = integral[i] + integral_increment
        
        # Anti-windup: clamp integral
        new_integral[i] = clamp(new_integral[i], -integral_limit, integral_limit)
        
        i_term = ki * new_integral[i]
        
        # Derivative term (backward difference)
        d_term = kd * (error[i] - prev_error[i]) / dt if dt > 0 else 0.0
        
        # Total output
        raw_output = p_term + i_term + d_term
        
        # Output saturation
        output[i] = clamp(raw_output, -output_limit, output_limit)
    
    return output, new_integral, list(error)


def compute_error(current_euler, setpoint):
    """Compute angular error between current orientation and setpoint.
    
    Handles wraparound for yaw (heading) axis.
    """
    error = [0.0, 0.0, 0.0]
    
    for i in range(3):
        err = setpoint[i] - current_euler[i]
        
        # Wrap yaw error to [-pi, pi]
        if i == 2:  # yaw axis
            err = wrap_angle(err)
        
        error[i] = err
    
    return error


def wrap_angle(angle):
    """Wrap angle to [-pi, pi] range."""
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def clamp(value, min_val, max_val):
    """Clamp value to [min_val, max_val] range."""
    return max(min_val, min(max_val, value))


def compute_motor_commands(pid_output, motor_config=None):
    """Convert PID output to individual motor commands.
    
    For a quadcopter-style configuration:
    - Motor 0 (front-left):  +roll, +pitch
    - Motor 1 (front-right): -roll, +pitch
    - Motor 2 (rear-left):   +roll, -pitch
    - Motor 3 (rear-right):  -roll, -pitch
    All motors receive yaw component.
    """
    roll_cmd, pitch_cmd, yaw_cmd = pid_output
    
    base_thrust = 0.5  # Hover thrust
    if motor_config and 'base_thrust' in motor_config:
        base_thrust = motor_config['base_thrust']
    
    motors = [
        base_thrust + roll_cmd + pitch_cmd + yaw_cmd,  # FL
        base_thrust - roll_cmd + pitch_cmd - yaw_cmd,  # FR
        base_thrust + roll_cmd - pitch_cmd - yaw_cmd,  # RL
        base_thrust - roll_cmd - pitch_cmd + yaw_cmd,  # RR
    ]
    
    # Clamp to [0, 1] range
    motors = [clamp(m, 0.0, 1.0) for m in motors]
    
    return motors


def compute_control_diagnostics(error, output, integral):
    """Compute control loop diagnostic metrics."""
    error_magnitude = math.sqrt(sum(e**2 for e in error))
    output_magnitude = math.sqrt(sum(o**2 for o in output))
    integral_magnitude = math.sqrt(sum(i**2 for i in integral))
    
    return {
        'error_magnitude': error_magnitude,
        'output_magnitude': output_magnitude,
        'integral_magnitude': integral_magnitude,
        'saturated': any(abs(o) >= 0.99 for o in output),
    }
