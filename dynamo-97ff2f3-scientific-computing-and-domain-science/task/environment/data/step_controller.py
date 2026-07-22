"""
Step size controller module for the ODE solver pipeline.

Implements adaptive step size control using the standard PI
(proportional-integral) controller. The step size is adjusted based
on the local error estimate to maintain accuracy while maximizing
efficiency.

For an embedded method of order p, the optimal step size scaling is:
    h_new = h * safety * (1/error_norm)^(1/(p+1))

The controller also enforces min/max step size bounds and limits
the rate of step size increase to prevent instability.
"""

import math


class StepSizeController:
    """
    Adaptive step size controller for ODE integration.

    Attributes
    ----------
    atol : float
        Absolute tolerance.
    rtol : float
        Relative tolerance.
    max_step : float
        Maximum allowed step size.
    min_step : float
        Minimum allowed step size.
    safety_factor : float
        Safety factor for step size reduction (typically 0.8-0.95).
    max_growth : float
        Maximum factor by which step can grow in one step.
    min_shrink : float
        Minimum factor to which step can shrink in one step.
    """

    def __init__(self, atol=1e-6, rtol=1e-3, max_step=1.0,
                 min_step=1e-12, safety_factor=0.9):
        self.atol = atol
        self.rtol = rtol
        self.max_step = max_step
        self.min_step = min_step
        self.safety_factor = safety_factor
        self.max_growth = 5.0
        self.min_shrink = 0.2


def compute_new_step_size(h_current, error_norm, controller):
    """
    Compute the new step size based on the local error estimate.

    Uses the standard step size formula for embedded RK methods:
        h_new = h * safety * (1/err)^exponent

    where the exponent is derived from the order of the error
    estimator. For the Dormand-Prince RK45 pair, the error estimator
    is 4th order, so the optimal exponent for step size adaptation
    is 1/order.

    Parameters
    ----------
    h_current : float
        Current step size.
    error_norm : float
        Scaled error norm from the current step.
    controller : StepSizeController
        Controller with configuration parameters.

    Returns
    -------
    float
        New step size (clamped to [min_step, max_step]).
    """
    if error_norm <= 0:
        # Error is zero — increase step by max growth
        return min(h_current * controller.max_growth, controller.max_step)

    # Exponent for step size scaling
    # For RK45: error estimator is order 4, so exponent = 1/4
    order_exponent = _step_size_exponent()

    # Compute optimal step size ratio
    factor = controller.safety_factor * (1.0 / error_norm) ** order_exponent

    # Clamp growth/shrink rate
    factor = max(controller.min_shrink, min(factor, controller.max_growth))

    h_new = h_current * factor

    # Apply absolute bounds
    h_new = max(controller.min_step, min(h_new, controller.max_step))

    return h_new


def _step_size_exponent():
    """
    Return the exponent for step size control.

    For an embedded Runge-Kutta pair where the error estimate is
    of order p, the optimal exponent for the step size controller
    is 1/p. For the Dormand-Prince RK4(5) pair, the local error
    estimate is 4th order accurate, giving exponent 1/4.

    Returns
    -------
    float
        Step size control exponent.
    """
    error_order = 4
    return 1.0 / error_order


def accept_step(error_norm):
    """
    Determine whether the current step should be accepted.

    A step is accepted if the scaled error norm is <= 1.0, meaning
    the local error satisfies the tolerance requirement.

    Parameters
    ----------
    error_norm : float
        Scaled error norm.

    Returns
    -------
    bool
        True if step should be accepted.
    """
    return error_norm <= 1.0


def estimate_initial_step(f, t0, y0, atol, rtol, order=5):
    """
    Estimate a good initial step size using the algorithm from
    Hairer, Norsett & Wanner (Solving ODEs I, Section II.4).

    Parameters
    ----------
    f : callable
        RHS function.
    t0 : float
        Initial time.
    y0 : list of float
        Initial state.
    atol : float
        Absolute tolerance.
    rtol : float
        Relative tolerance.
    order : int
        Order of the method.

    Returns
    -------
    float
        Estimated initial step size.
    """
    n = len(y0)

    # Compute scale factors
    sc = [atol + rtol * abs(y0[i]) for i in range(n)]

    # Norm of y0/sc
    d0 = math.sqrt(sum((y0[i] / sc[i]) ** 2 for i in range(n)) / n)

    # Norm of f(t0, y0)/sc
    f0 = f(t0, y0)
    d1 = math.sqrt(sum((f0[i] / sc[i]) ** 2 for i in range(n)) / n)

    # First guess
    if d0 < 1e-5 or d1 < 1e-5:
        h0 = 1e-6
    else:
        h0 = 0.01 * d0 / d1

    # Explicit Euler step
    y1 = [y0[i] + h0 * f0[i] for i in range(n)]
    f1 = f(t0 + h0, y1)

    # Norm of (f1 - f0) / sc
    d2 = math.sqrt(
        sum(((f1[i] - f0[i]) / sc[i]) ** 2 for i in range(n)) / n
    ) / h0

    # Second guess
    if max(d1, d2) <= 1e-15:
        h1 = max(1e-6, h0 * 1e-3)
    else:
        h1 = (0.01 / max(d1, d2)) ** (1.0 / (order + 1))

    return min(100 * h0, h1)
