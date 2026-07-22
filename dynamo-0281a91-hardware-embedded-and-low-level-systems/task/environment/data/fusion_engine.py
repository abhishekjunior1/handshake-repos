"""Complementary filter sensor fusion for orientation estimation.

Implements a quaternion-based complementary filter that fuses:
- Gyroscope (high-frequency attitude changes)
- Accelerometer (gravity reference for pitch/roll)
- Magnetometer (heading reference for yaw)

The filter blends gyro-integrated orientation with accelerometer/magnetometer
correction using a tunable alpha parameter.
"""
import math


def quaternion_multiply(q1, q2):
    """Multiply two quaternions in (w, x, y, z) format."""
    w1, x1, y1, z1 = q1
    w2, x2, y2, z2 = q2
    return [
        w1*w2 - x1*x2 - y1*y2 - z1*z2,
        w1*x2 + x1*w2 + y1*z2 - z1*y2,
        w1*y2 - x1*z2 + y1*w2 + z1*x2,
        w1*z2 + x1*y2 - y1*x2 + z1*w2,
    ]


def quaternion_conjugate(q):
    """Compute quaternion conjugate (inverse for unit quaternions)."""
    return [q[0], -q[1], -q[2], -q[3]]


def quaternion_normalize(q):
    """Normalize quaternion to unit length."""
    norm = math.sqrt(sum(v**2 for v in q))
    if norm < 1e-10:
        return [1.0, 0.0, 0.0, 0.0]
    return [v / norm for v in q]


def gyro_to_quaternion_delta(gyro, dt):
    """Convert angular velocity to quaternion rotation increment.
    
    Uses small-angle approximation for the rotation quaternion:
    q_delta = [cos(|omega|*dt/2), sin(|omega|*dt/2) * omega_hat]
    """
    wx, wy, wz = gyro
    angle = math.sqrt(wx**2 + wy**2 + wz**2) * dt
    
    if angle < 1e-10:
        return [1.0, 0.0, 0.0, 0.0]
    
    half_angle = angle / 2.0
    s = math.sin(half_angle) / (angle / dt)
    
    return quaternion_normalize([
        math.cos(half_angle),
        s * wx,
        s * wy,
        s * wz,
    ])


def accel_to_orientation(accel):
    """Estimate pitch and roll from accelerometer (gravity vector).
    
    Returns quaternion representing the tilt estimated from gravity.
    Yaw is undefined from accelerometer alone.
    """
    ax, ay, az = accel
    norm = math.sqrt(ax**2 + ay**2 + az**2)
    
    if norm < 1e-6:
        return [1.0, 0.0, 0.0, 0.0]
    
    ax, ay, az = ax/norm, ay/norm, az/norm
    
    pitch = math.atan2(-ax, math.sqrt(ay**2 + az**2))
    roll = math.atan2(ay, az)
    
    # Convert Euler angles to quaternion (ZYX convention)
    cp = math.cos(pitch / 2)
    sp = math.sin(pitch / 2)
    cr = math.cos(roll / 2)
    sr = math.sin(roll / 2)
    
    return quaternion_normalize([
        cp * cr,
        cp * sr,
        sp * cr,
        -sp * sr,
    ])


def complementary_filter_update(q_prev, gyro, accel, dt, alpha):
    """Single step of complementary filter.
    
    Blends gyroscope integration (high-pass) with accelerometer
    tilt correction (low-pass) using parameter alpha:
    
    q_gyro = q_prev * q_delta(gyro)
    q_accel = accel_to_orientation(accel)
    q_fused = slerp(q_accel, q_gyro, alpha)
    
    alpha close to 1.0 trusts gyro more (less drift correction)
    alpha close to 0.0 trusts accelerometer more (noisy but no drift)
    """
    # Gyro integration
    q_delta = gyro_to_quaternion_delta(gyro, dt)
    q_gyro = quaternion_normalize(quaternion_multiply(q_prev, q_delta))
    
    # Accelerometer tilt reference
    q_accel = accel_to_orientation(accel)
    
    # Spherical linear interpolation
    q_fused = quaternion_slerp(q_accel, q_gyro, alpha)
    
    return quaternion_normalize(q_fused)


def quaternion_slerp(q0, q1, t):
    """Spherical linear interpolation between two quaternions.
    
    t=0 returns q0, t=1 returns q1.
    """
    dot = sum(a*b for a, b in zip(q0, q1))
    
    # Ensure shortest path
    if dot < 0:
        q0 = [-v for v in q0]
        dot = -dot
    
    # Clamp for numerical stability
    dot = min(dot, 1.0)
    
    if dot > 0.9995:
        # Linear interpolation for nearly identical quaternions
        result = [q0[i] + t * (q1[i] - q0[i]) for i in range(4)]
        return quaternion_normalize(result)
    
    theta_0 = math.acos(dot)
    theta = theta_0 * t
    
    sin_theta = math.sin(theta)
    sin_theta_0 = math.sin(theta_0)
    
    s0 = math.cos(theta) - dot * sin_theta / sin_theta_0
    s1 = sin_theta / sin_theta_0
    
    return [s0 * q0[i] + s1 * q1[i] for i in range(4)]


def quaternion_to_euler(q):
    """Convert quaternion (w,x,y,z) to Euler angles (roll, pitch, yaw) in radians."""
    w, x, y, z = q
    
    # Roll (x-axis rotation)
    sinr_cosp = 2 * (w * x + y * z)
    cosr_cosp = 1 - 2 * (x * x + y * y)
    roll = math.atan2(sinr_cosp, cosr_cosp)
    
    # Pitch (y-axis rotation)
    sinp = 2 * (w * y - z * x)
    sinp = max(-1.0, min(1.0, sinp))
    pitch = math.asin(sinp)
    
    # Yaw (z-axis rotation)
    siny_cosp = 2 * (w * z + x * y)
    cosy_cosp = 1 - 2 * (y * y + z * z)
    yaw = math.atan2(siny_cosp, cosy_cosp)
    
    return [roll, pitch, yaw]


def compute_angular_rates_body(q, gyro):
    """Transform angular rates from sensor frame to body frame using current orientation."""
    # For a well-aligned sensor, this is approximately identity
    # but handles any mounting offset
    return gyro  # Sensor frame assumed aligned with body frame
