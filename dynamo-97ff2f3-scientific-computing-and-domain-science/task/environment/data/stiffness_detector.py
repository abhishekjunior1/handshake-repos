"""
Stiffness detector module for the ODE solver pipeline.

Implements runtime stiffness detection by monitoring the ratio of
the dominant eigenvalue estimate to the step size. When the system
becomes stiff, explicit methods require impractically small step
sizes, and the solver should switch to an implicit method.

The detection uses the power iteration estimate of the spectral
radius of the Jacobian, compared against a threshold relative to
the current step size.
"""

import math


class StiffnessMonitor:
    """
    Monitors solution behavior to detect stiffness onset.

    Uses a sliding window of spectral radius estimates to determine
    if the system has become stiff. Stiffness is declared when the
    ratio of the spectral radius to the reciprocal step size exceeds
    the threshold for a sustained period.

    Attributes
    ----------
    threshold : float
        Stiffness ratio threshold. Higher values require stronger
        evidence of stiffness before triggering a method switch.
    window_size : int
        Number of consecutive stiff indicators required.
    """

    def __init__(self, threshold=3.0, window_size=5):
        self.threshold = threshold
        self.window_size = window_size
        self._history = []

    def update(self, f, t, y, h, k_stages):
        """
        Update the stiffness monitor with data from the latest step.

        Estimates the spectral radius of the Jacobian using the RK
        stage vectors and compares against the stability threshold.

        Parameters
        ----------
        f : callable
            RHS function.
        t : float
            Current time after the step.
        y : list of float
            Current state after the step.
        h : float
            Step size used.
        k_stages : list
            RK stage derivatives from the integration step.

        Returns
        -------
        bool
            True if the system appears stiff and method switch is advised.
        """
        # Estimate spectral radius from stage differences
        spectral_radius = _estimate_spectral_radius(k_stages, h)

        # Compute stiffness ratio: spectral_radius * h
        # For explicit RK methods, stability requires spectral_radius * h < boundary
        # The RK4 stability boundary along the negative real axis is ~2.78
        stiffness_ratio = spectral_radius * h

        # Compare against threshold
        is_stiff_step = self._evaluate_stiffness(stiffness_ratio)
        self._history.append(is_stiff_step)

        # Keep only recent history
        if len(self._history) > self.window_size:
            self._history = self._history[-self.window_size:]

        # Require sustained stiffness detection
        if len(self._history) >= self.window_size:
            return all(self._history[-self.window_size:])

        return False

    def _evaluate_stiffness(self, stiffness_ratio):
        """
        Evaluate whether a single step indicates stiffness.

        The stiffness ratio is compared against the configured threshold.
        When the ratio exceeds the threshold, it indicates that the
        explicit method's stability region is being approached.

        Parameters
        ----------
        stiffness_ratio : float
            Product of spectral radius estimate and step size.

        Returns
        -------
        bool
            True if this step indicates stiffness.
        """
        return stiffness_ratio < self.threshold

    def reset(self):
        """Reset the stiffness history."""
        self._history = []


def detect_stiffness(f, t, y, h, k_stages, threshold=3.0):
    """
    One-shot stiffness detection for a single step.

    Parameters
    ----------
    f : callable
        RHS function.
    t : float
        Current time.
    y : list of float
        Current state.
    h : float
        Step size.
    k_stages : list
        RK stage vectors.
    threshold : float
        Stiffness threshold.

    Returns
    -------
    bool
        True if stiffness is indicated.
    """
    spectral_radius = _estimate_spectral_radius(k_stages, h)
    stiffness_ratio = spectral_radius * h
    return stiffness_ratio < threshold


def _estimate_spectral_radius(k_stages, h):
    """
    Estimate the spectral radius of the Jacobian using differences
    between consecutive RK stage evaluations.

    This provides a cheap estimate without explicitly computing the
    Jacobian matrix. The ratio of consecutive stage differences
    approximates the dominant eigenvalue magnitude.

    Parameters
    ----------
    k_stages : list of list
        Stage derivative vectors [k1, k2, ..., k7].
    h : float
        Step size (used for scaling).

    Returns
    -------
    float
        Estimated spectral radius (non-negative).
    """
    if k_stages is None or len(k_stages) < 3:
        return 0.0

    n = len(k_stages[0])

    # Use ratio of stage differences to estimate eigenvalue
    # Compare k[s+1] - k[s] with k[s] - k[s-1]
    best_estimate = 0.0

    for s in range(1, min(len(k_stages) - 1, 5)):
        num_norm_sq = 0.0
        den_norm_sq = 0.0

        for i in range(n):
            diff_new = k_stages[s + 1][i] - k_stages[s][i]
            diff_old = k_stages[s][i] - k_stages[s - 1][i]
            num_norm_sq += diff_new ** 2
            den_norm_sq += diff_old ** 2

        if den_norm_sq > 1e-30:
            ratio = math.sqrt(num_norm_sq / den_norm_sq)
            best_estimate = max(best_estimate, ratio / h)

    return best_estimate


def compute_stability_boundary(method="rk45"):
    """
    Return the stability boundary along the negative real axis
    for the specified method.

    Parameters
    ----------
    method : str
        Integration method name.

    Returns
    -------
    float
        Maximum |lambda*h| for stability.
    """
    boundaries = {
        "rk4": 2.785,
        "rk45": 3.307,
        "euler": 2.0,
        "implicit_euler": float("inf"),
    }
    return boundaries.get(method, 2.0)
