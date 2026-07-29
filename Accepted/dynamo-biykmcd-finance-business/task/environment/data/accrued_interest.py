"""
Accrued interest computation for fixed-income securities.

Calculates accrued interest from last coupon date to settlement date
using the bond's specified day-count convention. Handles ex-dividend
periods and supports all major market conventions.
"""

from datetime import date, timedelta
from typing import Optional

from day_count import day_count_fraction, days_accrued


def compute_accrued_interest(face_value: float, coupon_rate: float,
                             frequency: int, last_coupon_date: date,
                             next_coupon_date: date, settlement_date: date,
                             day_count_convention: str,
                             ex_dividend_days: int = 0) -> float:
    """
    Compute accrued interest for a bond at settlement.

    Accrued interest represents the portion of the next coupon payment
    that has been earned by the seller between the last coupon date and
    the settlement date.

    AI = (Face × Coupon Rate / Frequency) × DayCountFraction(last_coupon, settlement)

    Parameters
    ----------
    face_value : float
        Par/face value of the bond
    coupon_rate : float
        Annual coupon rate (decimal)
    frequency : int
        Number of coupon payments per year
    last_coupon_date : date
        Most recent coupon payment date
    next_coupon_date : date
        Next scheduled coupon date
    settlement_date : date
        Trade settlement date
    day_count_convention : str
        Day-count convention for fraction calculation
    ex_dividend_days : int
        Number of days before next coupon when bond goes ex-dividend

    Returns
    -------
    float
        Accrued interest amount
    """
    if coupon_rate == 0.0:
        return 0.0

    if settlement_date <= last_coupon_date:
        return 0.0

    ex_div_date = next_coupon_date - timedelta(days=ex_dividend_days)
    if ex_dividend_days > 0 and settlement_date >= ex_div_date:
        remaining_fraction = day_count_fraction(
            settlement_date, next_coupon_date, day_count_convention,
            period_start=last_coupon_date, period_end=next_coupon_date
        )
        coupon_per_period = face_value * coupon_rate / frequency
        return -coupon_per_period * remaining_fraction

    accrual_fraction = day_count_fraction(
        last_coupon_date, settlement_date, day_count_convention,
        period_start=last_coupon_date, period_end=next_coupon_date
    )

    coupon_per_period = face_value * coupon_rate / frequency
    accrued = coupon_per_period * accrual_fraction

    return accrued


def compute_clean_price(dirty_price: float, accrued_interest: float) -> float:
    """
    Compute clean (flat) price from dirty (full) price.

    Clean Price = Dirty Price - Accrued Interest

    Parameters
    ----------
    dirty_price : float
        Full market price including accrued interest
    accrued_interest : float
        Computed accrued interest

    Returns
    -------
    float
        Clean price
    """
    return dirty_price - accrued_interest


def compute_dirty_price(clean_price: float, accrued_interest: float) -> float:
    """
    Compute dirty (full) price from clean (flat) price.

    Dirty Price = Clean Price + Accrued Interest

    Parameters
    ----------
    clean_price : float
        Quoted market price
    accrued_interest : float
        Computed accrued interest

    Returns
    -------
    float
        Dirty (full) price
    """
    return clean_price + accrued_interest


def compute_settlement_date(trade_date: date, settlement_days: int,
                            holidays: Optional[list] = None) -> date:
    """
    Compute settlement date from trade date with business day adjustment.

    Adds settlement_days business days to trade_date, skipping weekends
    and optionally specified holidays.

    Parameters
    ----------
    trade_date : date
        Transaction execution date
    settlement_days : int
        Number of business days for settlement (e.g., 2 for T+2)
    holidays : list of date, optional
        Market holidays to skip

    Returns
    -------
    date
        Computed settlement date
    """
    if holidays is None:
        holidays = []

    current = trade_date
    days_added = 0

    while days_added < settlement_days:
        current += timedelta(days=1)
        if current.weekday() < 5 and current not in holidays:
            days_added += 1

    return current


def accrued_interest_zero_coupon(face_value: float, issue_date: date,
                                maturity_date: date, settlement_date: date,
                                issue_price: float) -> float:
    """
    Compute accrued interest for a zero-coupon bond (OID accrual).

    For zero-coupon bonds, accrued interest is based on the original issue
    discount (OID) that has economically accrued from issue to settlement.

    Uses constant-yield method for tax purposes.

    Parameters
    ----------
    face_value : float
        Par value at maturity
    issue_date : date
        Original issue date
    maturity_date : date
        Maturity date
    settlement_date : date
        Current settlement
    issue_price : float
        Original issue price

    Returns
    -------
    float
        Accrued OID
    """
    total_days = (maturity_date - issue_date).days
    if total_days <= 0:
        return 0.0

    elapsed_days = (settlement_date - issue_date).days
    if elapsed_days <= 0:
        return 0.0

    fraction_elapsed = elapsed_days / total_days
    total_discount = face_value - issue_price
    accrued_oid = total_discount * fraction_elapsed

    return accrued_oid
