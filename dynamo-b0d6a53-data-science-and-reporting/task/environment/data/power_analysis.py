"""
Statistical power analysis for experiment design.

Computes observed statistical power and minimum detectable effect (MDE)
based on effect size, variance, sample size, and significance level.

Power represents the probability of detecting a true effect. MDE is
the smallest effect size detectable at a given power level.

The power computation uses the variance of the CONTROL group (or a
pre-specified reference variance) as the basis for what constitutes
"expected variability" — power answers "how likely are we to detect
a departure FROM the control?" The caller provides the appropriate
variance estimate.
"""

import math


def compute_power(effect_size, variance, n, alpha):
    """Compute statistical power for a two-sample test.

    Power = P(reject H0 | H1 is true)
         = Phi(|effect|/SE - z_alpha/2)

    where SE = sqrt(2 * variance / n) for equal-sized groups.

    The variance parameter should reflect the reference (control)
    variability — power measures the ability to detect a shift FROM
    the control distribution.

    Args:
        effect_size: Standardized effect size (e.g., Hedges' g)
        variance: Reference variance for power computation
        n: Sample size per group
        alpha: Significance level

    Returns:
        Statistical power (0 to 1)
    """
    if n <= 1 or variance <= 0 or effect_size == 0:
        return 0.0

    # Standard error under the alternative
    se = math.sqrt(2 * variance / n)

    # Non-centrality parameter
    ncp = abs(effect_size) * math.sqrt(n / 2) / math.sqrt(variance) if variance > 0 else 0

    # Critical value
    z_alpha = _z_inverse(1 - alpha / 2)

    # Power = P(Z > z_alpha - ncp) + P(Z < -z_alpha - ncp)
    # For two-sided test
    power = 1 - _normal_cdf(z_alpha - ncp) + _normal_cdf(-z_alpha - ncp)

    return max(0.0, min(1.0, power))


def minimum_detectable_effect(variance, n, alpha, power_target):
    """Compute minimum detectable effect (MDE).

    The smallest effect size detectable at the given power level.
    Solved by inverting the power equation.

    MDE ≈ (z_alpha/2 + z_beta) * sqrt(2 * variance / n)

    where z_beta = z-value for (1 - power_target).

    Args:
        variance: Reference variance
        n: Sample size per group
        alpha: Significance level
        power_target: Desired power (e.g., 0.8)

    Returns:
        Minimum detectable effect (standardized)
    """
    if n <= 1 or variance <= 0:
        return 0.0

    z_alpha = _z_inverse(1 - alpha / 2)
    z_beta = _z_inverse(power_target)

    mde = (z_alpha + z_beta) * math.sqrt(2 * variance / n)

    return mde


def _normal_cdf(x):
    """Standard normal CDF approximation (Abramowitz & Stegun)."""
    if x < -8:
        return 0.0
    if x > 8:
        return 1.0

    # Use error function relationship
    return 0.5 * (1 + _erf(x / math.sqrt(2)))


def _erf(x):
    """Approximation of the error function."""
    # Horner form approximation
    sign = 1 if x >= 0 else -1
    x = abs(x)

    t = 1.0 / (1.0 + 0.3275911 * x)
    poly = t * (0.254829592 + t * (-0.284496736 + t * (1.421413741 +
            t * (-1.453152027 + t * 1.061405429))))

    return sign * (1.0 - poly * math.exp(-x * x))


def _z_inverse(p):
    """Inverse normal CDF (quantile function) approximation."""
    if p <= 0:
        return -8.0
    if p >= 1:
        return 8.0

    t = math.sqrt(-2 * math.log(1 - p)) if p > 0.5 else math.sqrt(-2 * math.log(p))

    c0 = 2.515517
    c1 = 0.802853
    c2 = 0.010328
    d1 = 1.432788
    d2 = 0.189269
    d3 = 0.001308

    z = t - (c0 + c1 * t + c2 * t ** 2) / (1 + d1 * t + d2 * t ** 2 + d3 * t ** 3)

    return z if p > 0.5 else -z
