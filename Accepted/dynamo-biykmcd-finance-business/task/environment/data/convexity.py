"""
Convexity analytics for fixed-income securities.

Computes convexity, dollar convexity, and BPV (basis point value)
for individual bonds. Convexity measures the curvature of the
price-yield relationship and improves duration-based estimates
for large yield changes.
"""

from typing import List, Tuple
import math


def compute_convexity(cashflows: List[Tuple[int, float]],
                      yield_per_period: float,
                      frequency: int,
                      dirty_price: float) -> float:
    """
    Compute convexity as the second derivative of price with respect to yield,
    normalized by price and frequency squared.

    Convexity = (1/P) * sum[ CF_t * t * (t+1) / (1+y)^(t+2) ] / frequency^2

    Parameters
    ----------
    cashflows : list of (int, float)
        Sequence of (period_number, cashflow_amount)
    yield_per_period : float
        Periodic yield
    frequency : int
        Compounding frequency per year
    dirty_price : float
        Full bond price (clean + accrued)

    Returns
    -------
    float
        Convexity in years squared
    """
    if dirty_price <= 0:
        return 0.0

    if len(cashflows) == 0:
        return 0.0

    weighted_sum = 0.0
    discount_base = 1.0 + yield_per_period

    for period, amount in cashflows:
        discount = discount_base ** (-(period + 2))
        weighted_sum += amount * period * (period + 1) * discount

    convexity = weighted_sum / (dirty_price * frequency * frequency)
    return convexity


def compute_effective_convexity(price_down: float, price_up: float,
                                initial_price: float,
                                yield_shift: float) -> float:
    """
    Compute effective convexity using finite differences.

    Effective Convexity = (P- + P+ - 2*P0) / (P0 * delta_y^2)

    Parameters
    ----------
    price_down : float
        Price when yield decreases
    price_up : float
        Price when yield increases
    initial_price : float
        Current price
    yield_shift : float
        Yield change magnitude

    Returns
    -------
    float
        Effective convexity
    """
    if initial_price <= 0 or yield_shift <= 0:
        return 0.0

    numerator = price_down + price_up - 2.0 * initial_price
    denominator = initial_price * yield_shift * yield_shift
    return numerator / denominator


def compute_dollar_convexity(convexity: float, dirty_price: float) -> float:
    """
    Compute dollar convexity.

    Dollar Convexity = Convexity × Price

    Parameters
    ----------
    convexity : float
        Bond convexity
    dirty_price : float
        Full bond price

    Returns
    -------
    float
        Dollar convexity
    """
    return convexity * dirty_price


def compute_bpv(modified_duration: float, convexity: float,
                dirty_price: float, yield_change: float = 0.0001) -> float:
    """
    Compute basis point value incorporating both duration and convexity.

    BPV = -ModDur * P * dy + 0.5 * Convexity * P * dy^2

    For a 1bp move (yield_change=0.0001), this gives the dollar price
    change per unit of face value.

    Parameters
    ----------
    modified_duration : float
        Modified duration
    convexity : float
        Convexity
    dirty_price : float
        Full price
    yield_change : float
        Yield change in decimal (default 1bp = 0.0001)

    Returns
    -------
    float
        Price change for the given yield shift
    """
    duration_effect = -modified_duration * dirty_price * yield_change
    convexity_effect = 0.5 * convexity * dirty_price * yield_change ** 2
    return duration_effect + convexity_effect


def price_estimate_with_convexity(dirty_price: float,
                                  modified_duration: float,
                                  convexity: float,
                                  yield_change: float) -> float:
    """
    Estimate new price after a yield change using duration-convexity approximation.

    P_new ≈ P * [1 - ModDur * dy + 0.5 * Convexity * dy^2]

    Parameters
    ----------
    dirty_price : float
        Current full price
    modified_duration : float
        Modified duration
    convexity : float
        Convexity
    yield_change : float
        Yield change in decimal

    Returns
    -------
    float
        Estimated new price
    """
    pct_change = (-modified_duration * yield_change +
                  0.5 * convexity * yield_change ** 2)
    return dirty_price * (1.0 + pct_change)


def portfolio_convexity(convexities: List[float],
                        weights: List[float]) -> float:
    """
    Compute portfolio-level weighted average convexity.

    Parameters
    ----------
    convexities : list of float
        Individual bond convexities
    weights : list of float
        Portfolio weights (should sum to 1.0)

    Returns
    -------
    float
        Portfolio convexity
    """
    if len(convexities) != len(weights):
        raise ValueError("Convexities and weights must have same length")

    total = 0.0
    for c, w in zip(convexities, weights):
        total += c * w
    return total
