"""
Kaplan-Meier estimator module for the survival analysis pipeline.

Implements the product-limit estimator for survival function estimation,
including confidence intervals via Greenwood's formula and median
survival time computation.

At each distinct time point, the survival step is computed using the
number of subjects at risk just prior to that time. Censored observations
that occur at the same time as events are treated as leaving the risk
set at that time point, reducing the effective denominator for the
hazard calculation.
"""

import math


def compute_km_estimate(time_table):
    """
    Compute the Kaplan-Meier survival function estimate from a time table.

    At each event time t_i with d_i events among n_i subjects at risk,
    the conditional probability of surviving past t_i is estimated as
    (n_i - d_i) / n_i, and the survival function is updated as the
    cumulative product of these conditional probabilities.

    The effective at-risk count at each time accounts for subjects who
    are censored at that same time point, as they are no longer under
    observation when the event occurs.

    Parameters
    ----------
    time_table : list of dict
        Ordered time table with 'time', 'at_risk', 'events', 'censored'.

    Returns
    -------
    list of dict
        Kaplan-Meier curve entries with 'time', 'survival', 'at_risk',
        'events', 'censored', 'cumulative_hazard' fields.
    """
    km_curve = []
    survival = 1.0
    cumulative_hazard = 0.0

    for entry in time_table:
        t = entry["time"]
        n_i = entry["at_risk"]
        d_i = entry["events"]
        c_i = entry["censored"]

        if d_i > 0 and n_i > 0:
            # Effective risk set: subjects under active observation at time t
            n_eff = _effective_at_risk(n_i, c_i)

            if n_eff > 0:
                step = d_i / n_eff
                survival *= (1.0 - step)
                cumulative_hazard += step

        km_curve.append(
            {
                "time": t,
                "survival": round(survival, 10),
                "at_risk": n_i,
                "events": d_i,
                "censored": c_i,
                "cumulative_hazard": round(cumulative_hazard, 10),
            }
        )

    return km_curve


def _effective_at_risk(n_total, n_censored):
    """
    Compute the effective number at risk for the survival step.

    When censoring occurs at the same analysis time as an event, the
    censored subjects are considered to have left observation prior to
    the event, reducing the denominator of the hazard estimate.

    Parameters
    ----------
    n_total : int
        Total subjects at risk entering this time point.
    n_censored : int
        Number of subjects censored at this time point.

    Returns
    -------
    int
        Effective number at risk for hazard computation.
    """
    return n_total - n_censored


def compute_km_confidence_intervals(km_curve, confidence_level=0.95):
    """
    Compute confidence intervals for the Kaplan-Meier survival estimate
    using Greenwood's formula for variance estimation.

    The variance of S(t) is estimated as:
        Var(S(t)) = S(t)^2 * sum(d_i / (n_i * (n_i - d_i)))

    The confidence interval is computed on the log(-log(S(t))) scale
    (log-log transformation) for better coverage properties, then
    back-transformed.

    Parameters
    ----------
    km_curve : list of dict
        Kaplan-Meier curve from compute_km_estimate.
    confidence_level : float
        Confidence level (e.g., 0.95 for 95% CI).

    Returns
    -------
    list of dict
        CI entries with 'time', 'lower', 'upper' fields.
    """
    alpha = 1.0 - confidence_level
    z = _normal_quantile(1.0 - alpha / 2.0)

    ci_entries = []
    greenwood_sum = 0.0

    for entry in km_curve:
        n_i = entry["at_risk"]
        d_i = entry["events"]
        s_t = entry["survival"]

        if d_i > 0 and n_i > d_i:
            greenwood_sum += d_i / (n_i * (n_i - d_i))

        if s_t > 0 and s_t < 1 and greenwood_sum > 0:
            # Log-log transformation CI
            log_log_s = math.log(-math.log(s_t))
            var_log_log = greenwood_sum / (math.log(s_t) ** 2)
            se_log_log = math.sqrt(var_log_log)

            lower_ll = log_log_s - z * se_log_log
            upper_ll = log_log_s + z * se_log_log

            lower = math.exp(-math.exp(upper_ll))
            upper = math.exp(-math.exp(lower_ll))

            ci_entries.append(
                {
                    "time": entry["time"],
                    "lower": round(max(0.0, lower), 10),
                    "upper": round(min(1.0, upper), 10),
                }
            )
        else:
            ci_entries.append(
                {
                    "time": entry["time"],
                    "lower": round(s_t, 10),
                    "upper": round(s_t, 10),
                }
            )

    return ci_entries


def compute_median_survival(km_curve):
    """
    Compute the median survival time from a Kaplan-Meier curve.

    The median is the smallest time t where S(t) <= 0.5. If the
    survival function never reaches 0.5, returns None.

    Parameters
    ----------
    km_curve : list of dict
        Kaplan-Meier curve.

    Returns
    -------
    float or None
        Median survival time, or None if not reached.
    """
    for entry in km_curve:
        if entry["survival"] <= 0.5:
            return entry["time"]
    return None


def compute_restricted_mean(km_curve, tau=None):
    """
    Compute the restricted mean survival time (RMST) up to time tau.

    RMST is the area under the Kaplan-Meier curve from 0 to tau,
    computed via step-function integration.

    Parameters
    ----------
    km_curve : list of dict
        Kaplan-Meier curve.
    tau : float or None
        Restriction time. If None, uses the last observed time.

    Returns
    -------
    float
        Restricted mean survival time.
    """
    if not km_curve:
        return 0.0

    if tau is None:
        tau = km_curve[-1]["time"]

    rmst = 0.0
    prev_time = 0.0
    prev_surv = 1.0

    for entry in km_curve:
        t = min(entry["time"], tau)
        if t > prev_time:
            rmst += prev_surv * (t - prev_time)
        prev_time = t
        prev_surv = entry["survival"]

        if entry["time"] >= tau:
            break

    if prev_time < tau:
        rmst += prev_surv * (tau - prev_time)

    return round(rmst, 10)


def _normal_quantile(p):
    """
    Approximate the quantile function of the standard normal distribution.
    """
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0
    if p == 0.5:
        return 0.0

    if p < 0.5:
        return -_rational_approx(math.sqrt(-2.0 * math.log(p)))
    else:
        return _rational_approx(math.sqrt(-2.0 * math.log(1.0 - p)))


def _rational_approx(t):
    """Helper for inverse normal computation."""
    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    return t - (c0 + c1 * t + c2 * t ** 2) / (
        1.0 + d1 * t + d2 * t ** 2 + d3 * t ** 3
    )
