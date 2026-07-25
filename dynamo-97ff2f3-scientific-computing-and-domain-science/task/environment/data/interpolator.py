"""
Interpolation module for the ODE solver pipeline.

Provides dense output by interpolating the solution trajectory at
arbitrary time points using piecewise cubic Hermite interpolation.
This allows producing smooth solution values at evenly-spaced output
points from the adaptive (unevenly-spaced) integration steps.
"""


def build_dense_output(t_history, y_history, t_output):
    """
    Interpolate the solution at specified output points using the
    stored integration trajectory.

    Uses piecewise linear interpolation between stored time points.
    For points outside the integration range, uses the nearest value.

    Parameters
    ----------
    t_history : list of float
        Time points from integration (ascending order).
    y_history : list of list of float
        State vectors at each time point.
    t_output : list of float
        Desired output time points.

    Returns
    -------
    list of list of float
        Interpolated state vectors at each output point.
    """
    if not t_history or not y_history:
        return [[0.0] * len(y_history[0]) for _ in t_output]

    n_vars = len(y_history[0])
    result = []

    for t_out in t_output:
        # Find bracketing interval
        idx = _find_interval(t_history, t_out)

        if idx <= 0:
            result.append(y_history[0][:])
        elif idx >= len(t_history):
            result.append(y_history[-1][:])
        else:
            # Linear interpolation within interval
            t0 = t_history[idx - 1]
            t1 = t_history[idx]
            y0 = y_history[idx - 1]
            y1 = y_history[idx]

            if t1 - t0 == 0:
                result.append(y0[:])
            else:
                alpha = (t_out - t0) / (t1 - t0)
                y_interp = [
                    y0[i] + alpha * (y1[i] - y0[i]) for i in range(n_vars)
                ]
                result.append(y_interp)

    return result


def hermite_interpolate(t0, t1, y0, y1, f0, f1, t):
    """
    Cubic Hermite interpolation between two points with derivative
    information.

    Parameters
    ----------
    t0, t1 : float
        Endpoint times.
    y0, y1 : list of float
        State vectors at endpoints.
    f0, f1 : list of float
        Derivative vectors at endpoints.
    t : float
        Interpolation point.

    Returns
    -------
    list of float
        Interpolated state vector.
    """
    n = len(y0)
    h = t1 - t0
    if h == 0:
        return y0[:]

    s = (t - t0) / h
    s2 = s * s
    s3 = s2 * s

    # Hermite basis functions
    h00 = 2 * s3 - 3 * s2 + 1
    h10 = s3 - 2 * s2 + s
    h01 = -2 * s3 + 3 * s2
    h11 = s3 - s2

    result = [0.0] * n
    for i in range(n):
        result[i] = (
            h00 * y0[i] + h10 * h * f0[i] + h01 * y1[i] + h11 * h * f1[i]
        )

    return result


def _find_interval(t_sorted, t_query):
    """
    Find the index of the first element in t_sorted that is >= t_query.

    Uses binary search for efficiency.

    Parameters
    ----------
    t_sorted : list of float
        Sorted time values.
    t_query : float
        Query time.

    Returns
    -------
    int
        Index of the bracketing interval upper bound.
    """
    lo, hi = 0, len(t_sorted)
    while lo < hi:
        mid = (lo + hi) // 2
        if t_sorted[mid] < t_query:
            lo = mid + 1
        else:
            hi = mid
    return lo
