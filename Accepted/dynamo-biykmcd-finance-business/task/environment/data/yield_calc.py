"""
Yield-to-maturity and yield calculation engine for fixed-income securities.

Implements Newton-Raphson iterative solver for YTM and related yield metrics.
Supports various compounding frequencies and handles zero-coupon and
coupon-bearing bonds.
"""

from typing import List, Tuple
import math


def compute_ytm(face_value: float, coupon_rate: float, price: float,
                periods_remaining: int, frequency: int,
                initial_guess: float = 0.05, tolerance: float = 1e-10,
                max_iterations: int = 200) -> float:
    """
    Compute yield-to-maturity using Newton-Raphson method.

    Parameters
    ----------
    face_value : float
        Par/face value of the bond
    coupon_rate : float
        Annual coupon rate (decimal, e.g., 0.05 for 5%)
    price : float
        Current market price (dirty price including accrued interest)
    periods_remaining : int
        Number of coupon periods until maturity
    frequency : int
        Coupon payments per year (1=annual, 2=semi-annual, 4=quarterly)
    initial_guess : float
        Starting yield for iteration
    tolerance : float
        Convergence tolerance for Newton-Raphson
    max_iterations : int
        Maximum iterations before giving up

    Returns
    -------
    float
        Annualized yield-to-maturity (decimal)
    """
    if periods_remaining <= 0:
        return 0.0

    if price <= 0:
        return 0.0

    coupon_per_period = face_value * coupon_rate / frequency

    if periods_remaining == 1:
        ytm_period = (face_value + coupon_per_period - price) / price
        return ytm_period * frequency

    y = initial_guess / frequency

    for iteration in range(max_iterations):
        pv, dpv = _bond_price_and_derivative(face_value, coupon_per_period,
                                             y, periods_remaining)
        error = pv - price
        if abs(error) < tolerance:
            break

        if abs(dpv) < 1e-15:
            break

        y = y - error / dpv

        if y < -0.5:
            y = -0.5
        elif y > 5.0:
            y = 5.0

    return y * frequency


def _bond_price_and_derivative(face_value: float, coupon: float,
                               yield_per_period: float,
                               periods: int) -> Tuple[float, float]:
    """
    Compute bond present value and its derivative with respect to yield.

    Uses closed-form annuity and principal PV formulas for efficiency.
    """
    if abs(yield_per_period) < 1e-12:
        pv = coupon * periods + face_value
        dpv = -coupon * periods * (periods + 1) / 2.0 - face_value * periods
        return pv, dpv

    discount = 1.0 / (1.0 + yield_per_period)
    discount_n = discount ** periods

    annuity_factor = (1.0 - discount_n) / yield_per_period
    pv_coupons = coupon * annuity_factor
    pv_principal = face_value * discount_n
    pv = pv_coupons + pv_principal

    d_annuity = (-periods * discount_n * discount / yield_per_period +
                 (discount_n - 1.0) / (yield_per_period ** 2))
    d_annuity = -d_annuity
    d_annuity_correct = ((-periods * (discount ** (periods + 1))) / yield_per_period -
                         (1.0 - discount_n) / (yield_per_period ** 2))

    d_principal = -periods * face_value * (discount ** (periods + 1))
    dpv = coupon * d_annuity_correct + d_principal

    return pv, dpv


def compute_current_yield(face_value: float, coupon_rate: float,
                          clean_price: float) -> float:
    """
    Compute current yield (annual coupon / clean price).

    Parameters
    ----------
    face_value : float
        Par value
    coupon_rate : float
        Annual coupon rate (decimal)
    clean_price : float
        Market clean price

    Returns
    -------
    float
        Current yield (decimal)
    """
    if clean_price <= 0:
        return 0.0
    annual_coupon = face_value * coupon_rate
    return annual_coupon / clean_price


def compute_running_yield(face_value: float, coupon_rate: float,
                          dirty_price: float) -> float:
    """
    Compute running yield (annual coupon / dirty price).

    Running yield accounts for accrued interest in the denominator,
    giving a more accurate yield for income-focused investors.
    """
    if dirty_price <= 0:
        return 0.0
    annual_coupon = face_value * coupon_rate
    return annual_coupon / dirty_price


def generate_cashflows(face_value: float, coupon_rate: float,
                       periods_remaining: int, frequency: int) -> List[Tuple[int, float]]:
    """
    Generate the sequence of future cashflows for a bond.

    Parameters
    ----------
    face_value : float
        Par value
    coupon_rate : float
        Annual coupon rate (decimal)
    periods_remaining : int
        Number of remaining coupon periods
    frequency : int
        Payments per year

    Returns
    -------
    list of (int, float)
        Each tuple is (period_number, cashflow_amount)
    """
    coupon_per_period = face_value * coupon_rate / frequency
    cashflows = []

    for t in range(1, periods_remaining + 1):
        cf = coupon_per_period
        if t == periods_remaining:
            cf += face_value
        cashflows.append((t, cf))

    return cashflows


def present_value_cashflows(cashflows: List[Tuple[int, float]],
                            yield_per_period: float) -> float:
    """
    Compute present value of a sequence of cashflows.

    Parameters
    ----------
    cashflows : list of (int, float)
        Period numbers and corresponding amounts
    yield_per_period : float
        Periodic discount rate

    Returns
    -------
    float
        Total present value
    """
    total_pv = 0.0
    for period, amount in cashflows:
        discount = (1.0 + yield_per_period) ** (-period)
        total_pv += amount * discount
    return total_pv
