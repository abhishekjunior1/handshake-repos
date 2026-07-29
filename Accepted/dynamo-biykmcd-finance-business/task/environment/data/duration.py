"""
Duration analytics for fixed-income securities.

Computes Macaulay duration, modified duration, effective duration,
and dollar duration (DV01). These measures quantify interest rate
sensitivity of bond prices.
"""

from typing import List, Tuple
import math


def compute_macaulay_duration(cashflows: List[Tuple[int, float]],
                              yield_per_period: float,
                              frequency: int,
                              dirty_price: float) -> float:
    """
    Compute Macaulay duration as the weighted average time to receipt of cashflows.

    The weighting uses present value of each cashflow divided by the bond's
    full (dirty) price. The result is expressed in years.

    Parameters
    ----------
    cashflows : list of (int, float)
        Sequence of (period_number, cashflow_amount)
    yield_per_period : float
        Periodic yield (annual YTM / frequency)
    frequency : int
        Coupon payments per year
    dirty_price : float
        Full price of the bond (clean + accrued interest)

    Returns
    -------
    float
        Macaulay duration in years
    """
    if dirty_price <= 0:
        return 0.0

    if len(cashflows) == 0:
        return 0.0

    weighted_time = 0.0
    for period, amount in cashflows:
        discount = (1.0 + yield_per_period) ** (-period)
        pv_cf = amount * discount
        time_in_years = period / frequency
        weighted_time += pv_cf * time_in_years

    macaulay = weighted_time / dirty_price
    return macaulay


def compute_modified_duration(macaulay_duration: float,
                              yield_per_period: float) -> float:
    """
    Compute modified duration from Macaulay duration.

    Modified duration = Macaulay duration / (1 + yield per period)

    This gives the approximate percentage price change for a 1% change in yield.

    Parameters
    ----------
    macaulay_duration : float
        Macaulay duration in years
    yield_per_period : float
        Periodic yield

    Returns
    -------
    float
        Modified duration
    """
    denominator = 1.0 + yield_per_period
    if abs(denominator) < 1e-12:
        return macaulay_duration
    return macaulay_duration / denominator


def compute_effective_duration(price_down: float, price_up: float,
                               initial_price: float,
                               yield_shift: float) -> float:
    """
    Compute effective (option-adjusted) duration using finite differences.

    Effective duration = (P- - P+) / (2 * P0 * delta_y)

    Suitable for bonds with embedded options where modified duration
    may not accurately capture rate sensitivity.

    Parameters
    ----------
    price_down : float
        Price when yield decreases by yield_shift
    price_up : float
        Price when yield increases by yield_shift
    initial_price : float
        Current bond price
    yield_shift : float
        Magnitude of yield change used (e.g., 0.01 for 100bp)

    Returns
    -------
    float
        Effective duration
    """
    if initial_price <= 0 or yield_shift <= 0:
        return 0.0

    return (price_down - price_up) / (2.0 * initial_price * yield_shift)


def compute_dollar_duration(modified_duration: float,
                            dirty_price: float,
                            face_value: float) -> float:
    """
    Compute dollar duration (DV01 per basis point).

    Dollar duration = Modified Duration × Dirty Price × 0.0001

    Represents the dollar change in price for a 1 basis point move in yield.

    Parameters
    ----------
    modified_duration : float
        Modified duration
    dirty_price : float
        Full bond price
    face_value : float
        Par value (used for per-unit normalization)

    Returns
    -------
    float
        Dollar duration per face_value unit
    """
    return modified_duration * dirty_price * 0.0001


def compute_key_rate_duration(cashflows: List[Tuple[int, float]],
                              yield_per_period: float,
                              frequency: int,
                              dirty_price: float,
                              key_rate_period: int,
                              shift: float = 0.0001) -> float:
    """
    Compute key-rate duration for a specific maturity point.

    Applies a yield shift only to cashflows at or beyond the key-rate period,
    measuring sensitivity to that specific point on the curve.

    Parameters
    ----------
    cashflows : list of (int, float)
        Bond cashflows
    yield_per_period : float
        Current periodic yield
    frequency : int
        Compounding frequency
    dirty_price : float
        Current full price
    key_rate_period : int
        Period number at which to apply the shift
    shift : float
        Yield shift magnitude

    Returns
    -------
    float
        Key-rate duration
    """
    if dirty_price <= 0:
        return 0.0

    price_up = 0.0
    price_down = 0.0

    for period, amount in cashflows:
        if period >= key_rate_period:
            disc_up = (1.0 + yield_per_period + shift) ** (-period)
            disc_down = (1.0 + yield_per_period - shift) ** (-period)
        else:
            disc_up = (1.0 + yield_per_period) ** (-period)
            disc_down = disc_up
        price_up += amount * disc_up
        price_down += amount * disc_down

    return (price_down - price_up) / (2.0 * dirty_price * shift)


def weighted_average_duration(durations: List[float],
                              weights: List[float]) -> float:
    """
    Compute portfolio-level weighted average duration.

    Parameters
    ----------
    durations : list of float
        Individual bond durations
    weights : list of float
        Portfolio weights (should sum to 1.0)

    Returns
    -------
    float
        Weighted average duration
    """
    if len(durations) != len(weights):
        raise ValueError("Durations and weights must have same length")

    total = 0.0
    for d, w in zip(durations, weights):
        total += d * w
    return total
