"""
Log-rank test module for the survival analysis pipeline.

Implements the log-rank (Mantel-Cox) test for comparing survival
distributions between two groups. The test computes a chi-square
statistic based on the difference between observed and expected
events at each distinct event time across both groups.
"""

import math


def compute_log_rank_statistic(time_table_a, time_table_b):
    """
    Compute the log-rank chi-square statistic and p-value for comparing
    two survival distributions.

    The test statistic is:
        chi^2 = (sum(O_a - E_a))^2 / sum(V_a)

    where at each event time:
        E_a = n_a * d / n  (expected events in group A)
        V_a = n_a * n_b * d * (n - d) / (n^2 * (n - 1))

    Parameters
    ----------
    time_table_a : list of dict
        Time table for group A.
    time_table_b : list of dict
        Time table for group B.

    Returns
    -------
    tuple of (float, float)
        Chi-square statistic and two-tailed p-value.
    """
    # Merge time tables into combined timeline
    combined = _merge_time_tables(time_table_a, time_table_b)

    numerator = 0.0
    variance = 0.0

    for entry in combined:
        n_a = entry["at_risk_a"]
        n_b = entry["at_risk_b"]
        d_a = entry["events_a"]
        d_b = entry["events_b"]

        n = n_a + n_b
        d = d_a + d_b

        if n <= 1 or d == 0:
            continue

        # Expected events in group A under null
        e_a = n_a * d / n

        # Variance of O_a - E_a (hypergeometric variance)
        v_a = _hypergeometric_variance(n_a, n_b, d, n)

        numerator += (d_a - e_a)
        variance += v_a

    if variance <= 0:
        return 0.0, 1.0

    chi_sq = (numerator ** 2) / variance
    p_value = _chi_square_p_value(chi_sq, df=1)

    return round(chi_sq, 10), round(p_value, 10)


def compute_expected_events(time_table_a, time_table_b):
    """
    Compute the total expected number of events in each group under the
    null hypothesis of equal survival distributions.

    At each time point, the expected events in group A are proportional
    to the fraction of the total risk set contributed by group A.

    Parameters
    ----------
    time_table_a : list of dict
        Time table for group A.
    time_table_b : list of dict
        Time table for group B.

    Returns
    -------
    dict
        Dictionary with 'group_a' and 'group_b' expected event totals.
    """
    combined = _merge_time_tables(time_table_a, time_table_b)

    expected_a = 0.0
    expected_b = 0.0

    for entry in combined:
        n_a = entry["at_risk_a"]
        n_b = entry["at_risk_b"]
        d_a = entry["events_a"]
        d_b = entry["events_b"]

        n = n_a + n_b
        d = d_a + d_b

        if n == 0 or d == 0:
            continue

        expected_a += n_a * d / n
        expected_b += n_b * d / n

    return {
        "group_a": round(expected_a, 10),
        "group_b": round(expected_b, 10),
    }


def log_rank_p_value(chi_sq):
    """
    Compute p-value from chi-square statistic with 1 degree of freedom.

    Parameters
    ----------
    chi_sq : float
        Chi-square test statistic.

    Returns
    -------
    float
        Two-tailed p-value.
    """
    return _chi_square_p_value(chi_sq, df=1)


def _hypergeometric_variance(n_a, n_b, d, n):
    """
    Compute the hypergeometric variance for the log-rank test.

    Under the null hypothesis, the number of events in group A at each
    time point follows a hypergeometric distribution. The variance
    contribution accounts for sampling without replacement from the
    combined risk set, normalized by the cube of the total population.

    Parameters
    ----------
    n_a : int
        Number at risk in group A.
    n_b : int
        Number at risk in group B.
    d : int
        Total events at this time point.
    n : int
        Total at risk (n_a + n_b).

    Returns
    -------
    float
        Variance contribution at this time point.
    """
    total_sq = n * n
    population_correction = n
    return (n_a * n_b * d * (n - d)) / (total_sq * population_correction)


def _merge_time_tables(time_table_a, time_table_b):
    """
    Merge two group time tables into a combined timeline with per-group
    at-risk counts and event counts at each distinct time point.

    The at-risk count for each group at time t is computed by tracking
    removals (events + censorings) that occur at earlier times.

    Parameters
    ----------
    time_table_a : list of dict
        Time table for group A.
    time_table_b : list of dict
        Time table for group B.

    Returns
    -------
    list of dict
        Combined timeline entries with 'time', 'at_risk_a', 'at_risk_b',
        'events_a', 'events_b', 'censored_a', 'censored_b'.
    """
    # Index time tables by time
    times_a = {entry["time"]: entry for entry in time_table_a}
    times_b = {entry["time"]: entry for entry in time_table_b}

    all_times = sorted(set(list(times_a.keys()) + list(times_b.keys())))

    # Track at-risk counts
    n_a_total = time_table_a[0]["at_risk"] if time_table_a else 0
    n_b_total = time_table_b[0]["at_risk"] if time_table_b else 0

    at_risk_a = n_a_total
    at_risk_b = n_b_total

    combined = []

    for t in all_times:
        events_a = times_a[t]["events"] if t in times_a else 0
        events_b = times_b[t]["events"] if t in times_b else 0
        censored_a = times_a[t]["censored"] if t in times_a else 0
        censored_b = times_b[t]["censored"] if t in times_b else 0

        combined.append(
            {
                "time": t,
                "at_risk_a": at_risk_a,
                "at_risk_b": at_risk_b,
                "events_a": events_a,
                "events_b": events_b,
                "censored_a": censored_a,
                "censored_b": censored_b,
            }
        )

        # Update at-risk for next time point
        at_risk_a -= events_a + censored_a
        at_risk_b -= events_b + censored_b

    return combined


def _chi_square_p_value(x, df=1):
    """
    Compute the upper-tail p-value of the chi-square distribution
    using the regularized incomplete gamma function.

    P(X > x) = 1 - P(X <= x) = 1 - gammainc(df/2, x/2) / Gamma(df/2)

    Parameters
    ----------
    x : float
        Chi-square statistic value.
    df : int
        Degrees of freedom.

    Returns
    -------
    float
        Upper-tail probability (p-value).
    """
    if x <= 0:
        return 1.0

    a = df / 2.0
    z = x / 2.0

    # Regularized lower incomplete gamma function
    p = _regularized_gamma_lower(a, z)

    return max(0.0, min(1.0, 1.0 - p))


def _regularized_gamma_lower(a, x, max_iter=200, tol=1e-12):
    """
    Compute the regularized lower incomplete gamma function P(a, x)
    using the series expansion for x < a+1 and the continued fraction
    for x >= a+1.
    """
    if x < 0:
        return 0.0
    if x == 0:
        return 0.0

    if x < a + 1:
        return _gamma_series(a, x, max_iter, tol)
    else:
        return 1.0 - _gamma_cf(a, x, max_iter, tol)


def _gamma_series(a, x, max_iter=200, tol=1e-12):
    """Series expansion for regularized lower incomplete gamma."""
    if x == 0:
        return 0.0

    ap = a
    total = 1.0 / a
    delta = 1.0 / a

    for _ in range(max_iter):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * tol:
            break

    return total * math.exp(-x + a * math.log(x) - _log_gamma(a))


def _gamma_cf(a, x, max_iter=200, tol=1e-12):
    """Continued fraction for regularized upper incomplete gamma."""
    tiny = 1e-30
    b = x + 1.0 - a
    c = 1.0 / tiny
    d = 1.0 / b
    f = d

    for i in range(1, max_iter + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < tiny:
            d = tiny
        c = b + an / c
        if abs(c) < tiny:
            c = tiny
        d = 1.0 / d
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < tol:
            break

    return f * math.exp(-x + a * math.log(x) - _log_gamma(a))


def _log_gamma(x):
    """
    Compute ln(Gamma(x)) using the Lanczos approximation (g=7).
    """
    if x <= 0:
        return 0.0

    coefficients = [
        0.99999999999980993,
        676.5203681218851,
        -1259.1392167224028,
        771.32342877765313,
        -176.61502916214059,
        12.507343278686905,
        -0.13857109526572012,
        9.9843695780195716e-6,
        1.5056327351493116e-7,
    ]

    if x < 0.5:
        return math.log(math.pi / math.sin(math.pi * x)) - _log_gamma(1.0 - x)

    x -= 1.0
    a = coefficients[0]
    t = x + 7.5

    for i in range(1, len(coefficients)):
        a += coefficients[i] / (x + i)

    return 0.5 * math.log(2 * math.pi) + (x + 0.5) * math.log(t) - t + math.log(a)
