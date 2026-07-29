"""
Runge-Kutta methods module for the ODE solver pipeline.

Implements the Dormand-Prince RK45 pair (4th order solution with 5th
order error estimate), classical RK4, and implicit Euler for stiff
systems. Also provides the embedded error computation using the
tolerance-scaled norm.
"""

import math


# Dormand-Prince RK45 coefficients (Butcher tableau)
_DP_A = [
    [],
    [1.0 / 5.0],
    [3.0 / 40.0, 9.0 / 40.0],
    [44.0 / 45.0, -56.0 / 15.0, 32.0 / 9.0],
    [19372.0 / 6561.0, -25360.0 / 2187.0, 64448.0 / 6561.0, -212.0 / 729.0],
    [9017.0 / 3168.0, -355.0 / 33.0, 46732.0 / 5247.0, 49.0 / 176.0, -5103.0 / 18656.0],
    [35.0 / 384.0, 0.0, 500.0 / 1113.0, 125.0 / 192.0, -2187.0 / 6784.0, 11.0 / 84.0],
]

_DP_C = [0.0, 1.0 / 5.0, 3.0 / 10.0, 4.0 / 5.0, 8.0 / 9.0, 1.0, 1.0]

# 5th order weights (for propagation)
_DP_B = [35.0 / 384.0, 0.0, 500.0 / 1113.0, 125.0 / 192.0, -2187.0 / 6784.0, 11.0 / 84.0, 0.0]

# 4th order weights (for error estimation)
_DP_B_HAT = [
    5179.0 / 57600.0, 0.0, 7571.0 / 16695.0, 393.0 / 640.0,
    -92097.0 / 339200.0, 187.0 / 2100.0, 1.0 / 40.0,
]


def rk45_step(f, t, y, h):
    """
    Perform one step of the Dormand-Prince RK45 method.

    Returns the 5th-order solution (for propagation), the error estimate
    (difference between 4th and 5th order), and the intermediate stages.

    Parameters
    ----------
    f : callable
        RHS function f(t, y) returning dy/dt.
    t : float
        Current time.
    y : list of float
        Current state vector.
    h : float
        Step size.

    Returns
    -------
    tuple of (list, list, list)
        (y_new, y_err, k_stages) where y_new is the 5th-order solution,
        y_err is the error estimate, and k_stages are the RK stages.
    """
    n = len(y)
    k = [None] * 7

    # Stage 1
    k[0] = f(t, y)

    # Stages 2-7
    for s in range(1, 7):
        t_s = t + _DP_C[s] * h
        y_s = [0.0] * n
        for i in range(n):
            y_s[i] = y[i]
            for j in range(s):
                y_s[i] += h * _DP_A[s][j] * k[j][i]
        k[s] = f(t_s, y_s)

    # 5th order solution (propagated value)
    y_new = [0.0] * n
    for i in range(n):
        y_new[i] = y[i]
        for s in range(7):
            y_new[i] += h * _DP_B[s] * k[s][i]

    # Error estimate (difference between 4th and 5th order)
    y_err = [0.0] * n
    for i in range(n):
        for s in range(7):
            y_err[i] += h * (_DP_B[s] - _DP_B_HAT[s]) * k[s][i]

    return y_new, y_err, k


def rk4_step(f, t, y, h):
    """
    Perform one step of the classical 4th-order Runge-Kutta method.

    Parameters
    ----------
    f : callable
        RHS function f(t, y).
    t : float
        Current time.
    y : list of float
        Current state.
    h : float
        Step size.

    Returns
    -------
    list of float
        New state after one RK4 step.
    """
    n = len(y)

    k1 = f(t, y)
    y2 = [y[i] + 0.5 * h * k1[i] for i in range(n)]
    k2 = f(t + 0.5 * h, y2)
    y3 = [y[i] + 0.5 * h * k2[i] for i in range(n)]
    k3 = f(t + 0.5 * h, y3)
    y4 = [y[i] + h * k3[i] for i in range(n)]
    k4 = f(t + h, y4)

    y_new = [0.0] * n
    for i in range(n):
        y_new[i] = y[i] + (h / 6.0) * (k1[i] + 2.0 * k2[i] + 2.0 * k3[i] + k4[i])

    return y_new


def implicit_euler_step(f, t, y, h, tol=1e-10, max_iter=50):
    """
    Perform one step of the implicit (backward) Euler method using
    fixed-point iteration.

    Solves: y_{n+1} = y_n + h * f(t_{n+1}, y_{n+1})

    Parameters
    ----------
    f : callable
        RHS function f(t, y).
    t : float
        Current time.
    y : list of float
        Current state.
    h : float
        Step size.
    tol : float
        Convergence tolerance for fixed-point iteration.
    max_iter : int
        Maximum iterations.

    Returns
    -------
    list of float
        New state after one implicit Euler step.
    """
    n = len(y)
    t_new = t + h

    # Initial guess: explicit Euler
    y_new = [y[i] + h * f(t, y)[i] for i in range(n)]

    for _ in range(max_iter):
        f_new = f(t_new, y_new)
        y_next = [y[i] + h * f_new[i] for i in range(n)]

        # Check convergence
        max_diff = max(abs(y_next[i] - y_new[i]) for i in range(n))
        y_new = y_next

        if max_diff < tol:
            break

    return y_new


def compute_embedded_error(y, y_new, y_err, atol, rtol):
    """
    Compute the scaled error norm for step size control.

    The error for each component is scaled by the tolerance:
        sc_i = atol + rtol * max(|y_i|, |y_new_i|)

    The overall error norm is the RMS of the scaled errors:
        err = sqrt(mean((y_err_i / sc_i)^2))

    A value <= 1.0 means the step satisfies the tolerance requirement.

    Parameters
    ----------
    y : list of float
        State at beginning of step.
    y_new : list of float
        State at end of step.
    y_err : list of float
        Error estimate for each component.
    atol : float
        Absolute tolerance.
    rtol : float
        Relative tolerance.

    Returns
    -------
    float
        Scaled RMS error norm.
    """
    n = len(y)
    if n == 0:
        return 0.0

    sum_sq = 0.0
    for i in range(n):
        # Scale factor for this component
        scale = atol
        err_scaled = y_err[i] / scale if scale > 0 else 0.0
        sum_sq += err_scaled ** 2

    return math.sqrt(sum_sq / n)
