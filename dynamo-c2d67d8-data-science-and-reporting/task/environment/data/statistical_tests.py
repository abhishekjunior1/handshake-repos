"""
Statistical tests module for the biostatistics pipeline.

Implements hypothesis testing procedures including Welch's t-test,
Mann-Whitney U test, and multiple comparison correction methods
(Bonferroni, Holm-Bonferroni).
"""

import math


def compute_test_statistics(data_a, data_b, test_type="welch_t"):
    """
    Compute the test statistic and p-value for a two-sample comparison.

    Parameters
    ----------
    data_a : list of float
        Measurements from group A.
    data_b : list of float
        Measurements from group B.
    test_type : str
        Type of test to perform: 'welch_t' or 'mann_whitney'.

    Returns
    -------
    tuple of (float, float)
        Test statistic and p-value.
    """
    if test_type == "welch_t":
        return _welch_t_test(data_a, data_b)
    elif test_type == "mann_whitney":
        return _mann_whitney_u(data_a, data_b)
    else:
        raise ValueError(f"Unsupported test type: {test_type}")


def run_group_comparisons(preprocessed_groups, comparisons, test_type="welch_t"):
    """
    Run all pairwise group comparisons specified in the study configuration.

    Parameters
    ----------
    preprocessed_groups : dict
        Dictionary mapping group names to preprocessed measurement lists.
    comparisons : list of dict
        Each dict has 'group_a' and 'group_b' keys.
    test_type : str
        Statistical test to use.

    Returns
    -------
    list of dict
        Raw results with test statistics and p-values for each comparison.
    """
    results = []
    for comp in comparisons:
        group_a = comp["group_a"]
        group_b = comp["group_b"]

        data_a = preprocessed_groups[group_a]
        data_b = preprocessed_groups[group_b]

        test_stat, p_value = compute_test_statistics(data_a, data_b, test_type)

        results.append(
            {
                "comparison": f"{group_a}_vs_{group_b}",
                "group_a": group_a,
                "group_b": group_b,
                "test_statistic": test_stat,
                "p_value": p_value,
                "test_type": test_type,
            }
        )

    return results


def apply_multiple_comparison_correction(results, method="holm", alpha=0.05):
    """
    Apply multiple comparison correction to a set of test results.

    Adjusts p-values and determines significance after correcting for
    the familywise error rate using the specified method.

    Parameters
    ----------
    results : list of dict
        Each dict must contain 'p_value' key.
    method : str
        Correction method: 'bonferroni' or 'holm' (Holm-Bonferroni).
    alpha : float
        Significance threshold before correction.

    Returns
    -------
    list of dict
        Results with added 'adjusted_p_value', 'significant', and 'rank' fields.
    """
    n_comparisons = len(results)

    if n_comparisons == 0:
        return results

    if method == "bonferroni":
        return _bonferroni_correction(results, n_comparisons, alpha)
    elif method == "holm":
        return _holm_bonferroni_correction(results, n_comparisons, alpha)
    else:
        raise ValueError(f"Unsupported correction method: {method}")


def _bonferroni_correction(results, n_comparisons, alpha):
    """
    Apply Bonferroni correction: multiply each p-value by the number
    of comparisons and compare against alpha.
    """
    corrected = []
    for result in results:
        adjusted_p = min(result["p_value"] * n_comparisons, 1.0)
        entry = dict(result)
        entry["adjusted_p_value"] = adjusted_p
        entry["significant"] = adjusted_p < alpha
        entry["correction_method"] = "bonferroni"
        corrected.append(entry)
    return corrected


def _holm_bonferroni_correction(results, n_comparisons, alpha):
    """
    Apply Holm-Bonferroni step-down correction.

    The procedure sorts p-values, then compares each against a progressively
    less stringent threshold. Once a p-value fails to reject, all subsequent
    comparisons are also marked non-significant.
    """
    # Create indexed list for sorting
    indexed = [(i, results[i]["p_value"]) for i in range(n_comparisons)]

    # Sort by p-value for step-down procedure
    indexed.sort(key=lambda x: x[1], reverse=True)

    # Apply step-down correction
    corrected = [None] * n_comparisons
    rejected_so_far = True

    for rank, (orig_idx, p_val) in enumerate(indexed):
        step = n_comparisons - rank
        adjusted_p = min(p_val * step, 1.0)

        # Enforce monotonicity
        if rank > 0:
            prev_idx = indexed[rank - 1][0]
            prev_adjusted = corrected[prev_idx]["adjusted_p_value"]
            adjusted_p = max(adjusted_p, prev_adjusted)

        # Once we fail to reject, all subsequent are also non-significant
        if rejected_so_far and adjusted_p >= alpha:
            rejected_so_far = False

        entry = dict(results[orig_idx])
        entry["adjusted_p_value"] = round(adjusted_p, 10)
        entry["significant"] = adjusted_p < alpha and rejected_so_far
        entry["correction_method"] = "holm"
        entry["rank"] = rank + 1
        corrected[orig_idx] = entry

    return corrected


def _welch_t_test(data_a, data_b):
    """
    Perform Welch's t-test for two independent samples with unequal variances.

    Returns
    -------
    tuple of (float, float)
        t-statistic and two-tailed p-value.
    """
    n_a = len(data_a)
    n_b = len(data_b)

    mean_a = sum(data_a) / n_a
    mean_b = sum(data_b) / n_b

    var_a = sum((x - mean_a) ** 2 for x in data_a) / (n_a - 1)
    var_b = sum((x - mean_b) ** 2 for x in data_b) / (n_b - 1)

    se_a = var_a / n_a
    se_b = var_b / n_b
    se_diff = math.sqrt(se_a + se_b)

    if se_diff == 0:
        return 0.0, 1.0

    t_stat = (mean_a - mean_b) / se_diff

    # Welch-Satterthwaite degrees of freedom
    numerator = (se_a + se_b) ** 2
    denominator = (se_a ** 2) / (n_a - 1) + (se_b ** 2) / (n_b - 1)

    if denominator == 0:
        df = n_a + n_b - 2
    else:
        df = numerator / denominator

    p_value = _t_distribution_two_tailed_p(t_stat, df)

    return round(t_stat, 10), round(p_value, 10)


def _mann_whitney_u(data_a, data_b):
    """
    Perform the Mann-Whitney U test for two independent samples.

    Uses the normal approximation for the U statistic when sample
    sizes are sufficiently large.

    Returns
    -------
    tuple of (float, float)
        U-statistic and two-tailed p-value.
    """
    n_a = len(data_a)
    n_b = len(data_b)

    # Assign ranks to combined data
    combined = [(val, "a", i) for i, val in enumerate(data_a)]
    combined += [(val, "b", i) for i, val in enumerate(data_b)]
    combined.sort(key=lambda x: x[0])

    # Handle ties by averaging ranks
    ranks = [0.0] * len(combined)
    i = 0
    while i < len(combined):
        j = i
        while j < len(combined) and combined[j][0] == combined[i][0]:
            j += 1
        avg_rank = (i + j + 1) / 2.0  # 1-based ranking
        for k in range(i, j):
            ranks[k] = avg_rank
        i = j

    # Sum ranks for group A
    rank_sum_a = sum(
        ranks[k] for k in range(len(combined)) if combined[k][1] == "a"
    )

    u_a = rank_sum_a - (n_a * (n_a + 1)) / 2.0
    u_b = n_a * n_b - u_a
    u_stat = min(u_a, u_b)

    # Normal approximation
    mean_u = (n_a * n_b) / 2.0
    std_u = math.sqrt((n_a * n_b * (n_a + n_b + 1)) / 12.0)

    if std_u == 0:
        return u_stat, 1.0

    z = (u_stat - mean_u) / std_u
    p_value = 2.0 * _standard_normal_cdf(z)

    return round(u_stat, 10), round(min(p_value, 1.0), 10)


def _t_distribution_two_tailed_p(t_stat, df):
    """
    Approximate two-tailed p-value from t-distribution using the
    regularized incomplete beta function approximation.
    """
    x = df / (df + t_stat ** 2)
    p = _regularized_incomplete_beta(df / 2.0, 0.5, x)
    return min(p, 1.0)


def _regularized_incomplete_beta(a, b, x):
    """
    Compute the regularized incomplete beta function I_x(a, b) using
    a continued fraction expansion (Lentz's method).
    """
    if x < 0 or x > 1:
        return 0.0
    if x == 0 or x == 1:
        return x

    # Use the symmetry relation if x > (a+1)/(a+b+2)
    if x > (a + 1.0) / (a + b + 2.0):
        return 1.0 - _regularized_incomplete_beta(b, a, 1.0 - x)

    # Log of the beta function prefix
    ln_prefix = (
        _log_gamma(a + b)
        - _log_gamma(a)
        - _log_gamma(b)
        + a * math.log(x)
        + b * math.log(1.0 - x)
    )

    prefix = math.exp(ln_prefix)

    # Continued fraction (Lentz's method)
    cf = _beta_continued_fraction(a, b, x)

    return prefix * cf / a


def _beta_continued_fraction(a, b, x, max_iter=200, tol=1e-12):
    """Evaluate continued fraction for incomplete beta function."""
    tiny = 1e-30
    f = tiny
    c = tiny
    d = 0.0

    for m in range(max_iter):
        if m == 0:
            numerator = 1.0
        else:
            k = m
            if k % 2 == 0:
                # Even term
                j = k // 2
                numerator = (j * (b - j) * x) / (
                    (a + 2 * j - 1) * (a + 2 * j)
                )
            else:
                # Odd term
                j = (k + 1) // 2
                numerator = -(
                    (a + j - 1 + j * b) * (a + j) * x
                    if j == 1
                    else (a + j - 1) * (a + b + j - 1) * x
                ) / ((a + 2 * j - 2) * (a + 2 * j - 1))
                # Corrected odd numerator
                numerator = -(a + j - 1 + (b - j) * 0) * x
                j_val = (k - 1) // 2 + 1
                numerator = (
                    -((a + j_val - 1) * (a + b + j_val - 1) * x)
                    / ((a + 2 * j_val - 2) * (a + 2 * j_val - 1))
                )

        d = 1.0 + numerator * d
        if abs(d) < tiny:
            d = tiny
        d = 1.0 / d

        c = 1.0 + numerator / c
        if abs(c) < tiny:
            c = tiny

        delta = c * d
        f *= delta

        if abs(delta - 1.0) < tol:
            break

    return f


def _log_gamma(x):
    """
    Compute ln(Gamma(x)) using Stirling's approximation with
    Lanczos coefficients for improved accuracy.
    """
    if x <= 0:
        return 0.0

    # Lanczos approximation (g=7)
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


def _standard_normal_cdf(z):
    """
    Compute the CDF of the standard normal distribution using
    the Abramowitz and Stegun approximation (formula 7.1.26).
    """
    if z < -8.0:
        return 0.0
    if z > 8.0:
        return 1.0

    a1 = 0.254829592
    a2 = -0.284496736
    a3 = 1.421413741
    a4 = -1.453152027
    a5 = 1.061405429
    p = 0.3275911

    sign = 1.0
    if z < 0:
        sign = -1.0
    z_abs = abs(z) / math.sqrt(2.0)

    t = 1.0 / (1.0 + p * z_abs)
    y = 1.0 - (
        ((((a5 * t + a4) * t) + a3) * t + a2) * t + a1
    ) * t * math.exp(-(z_abs ** 2))

    return 0.5 * (1.0 + sign * y)
