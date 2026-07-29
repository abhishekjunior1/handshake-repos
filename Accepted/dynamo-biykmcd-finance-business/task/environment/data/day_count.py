"""
Day-count convention calculations for fixed-income analytics.

Implements standard day-count fraction methods used in bond markets:
- ACT/ACT (ISDA): actual days / actual days in period
- ACT/360: actual days / 360
- ACT/365: actual days / 365
- 30/360 (Bond Basis): 30-day months / 360
- 30E/360 (Eurobond): European 30/360 variant
"""

from datetime import date, timedelta
from typing import Tuple


def _days_between(start: date, end: date) -> int:
    """Compute actual calendar days between two dates."""
    return (end - start).days


def _is_leap_year(year: int) -> bool:
    """Check if a year is a leap year per Gregorian calendar."""
    return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)


def _days_in_year(year: int) -> int:
    """Return number of days in a given year."""
    return 366 if _is_leap_year(year) else 365


def _adjust_day_30(day: int, month: int, year: int, end_of_month: bool = False) -> int:
    """Adjust day component for 30/360 calculation per ISDA rules."""
    if day == 31:
        return 30
    if month == 2:
        if _is_leap_year(year) and day == 29:
            if end_of_month:
                return 30
        elif not _is_leap_year(year) and day == 28:
            if end_of_month:
                return 30
    return day


def day_count_fraction(start_date: date, end_date: date, convention: str,
                       period_start: date = None, period_end: date = None) -> float:
    """
    Calculate the day-count fraction between two dates under specified convention.

    Parameters
    ----------
    start_date : date
        Start of accrual period (typically last coupon date or settlement)
    end_date : date
        End of accrual period (typically settlement date or next coupon date)
    convention : str
        Day-count convention identifier. One of:
        'ACT/ACT', 'ACT/360', 'ACT/365', '30/360', '30E/360'
    period_start : date, optional
        Start of current coupon period (for ACT/ACT ISDA reference period)
    period_end : date, optional
        End of current coupon period (for ACT/ACT ISDA reference period)

    Returns
    -------
    float
        Day-count fraction representing the portion of the period elapsed.
    """
    if start_date >= end_date:
        return 0.0

    convention = convention.upper().strip()

    if convention == "ACT/ACT":
        return _act_act_fraction(start_date, end_date, period_start, period_end)
    elif convention == "ACT/360":
        return _act_360_fraction(start_date, end_date)
    elif convention == "ACT/365":
        return _act_365_fraction(start_date, end_date)
    elif convention == "30/360":
        return _thirty_360_fraction(start_date, end_date)
    elif convention == "30E/360":
        return _thirty_e_360_fraction(start_date, end_date)
    else:
        raise ValueError(f"Unsupported day-count convention: {convention}")


def _act_act_fraction(start: date, end: date, period_start: date = None,
                      period_end: date = None) -> float:
    """
    ACT/ACT (ISDA) day-count fraction.

    Uses actual days in each year when the period spans multiple years.
    When a reference period is provided, uses the period length as denominator.
    """
    if period_start is not None and period_end is not None:
        period_days = _days_between(period_start, period_end)
        if period_days > 0:
            actual_days = _days_between(start, end)
            return actual_days / period_days
        return 0.0

    if start.year == end.year:
        actual_days = _days_between(start, end)
        year_days = _days_in_year(start.year)
        return actual_days / year_days

    fraction = 0.0
    year_end_first = date(start.year, 12, 31)
    days_first_year = _days_between(start, year_end_first) + 1
    fraction += days_first_year / _days_in_year(start.year)

    for year in range(start.year + 1, end.year):
        fraction += 1.0

    if end > date(end.year, 1, 1):
        year_start_last = date(end.year, 1, 1)
        days_last_year = _days_between(year_start_last, end)
        fraction += days_last_year / _days_in_year(end.year)

    return fraction


def _act_360_fraction(start: date, end: date) -> float:
    """ACT/360 day-count fraction. Actual days divided by 360."""
    actual_days = _days_between(start, end)
    return actual_days / 360.0


def _act_365_fraction(start: date, end: date) -> float:
    """ACT/365 Fixed day-count fraction. Actual days divided by 365."""
    actual_days = _days_between(start, end)
    return actual_days / 365.0


def _thirty_360_fraction(start: date, end: date) -> float:
    """
    30/360 Bond Basis (US) day-count fraction.

    Adjusts start and end day components per ISDA 2006 rules:
    - If D1 = 31, set D1 = 30
    - If D2 = 31 and D1 >= 30, set D2 = 30
    """
    d1 = start.day
    d2 = end.day
    m1 = start.month
    m2 = end.month
    y1 = start.year
    y2 = end.year

    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 >= 30:
        d2 = 30

    day_count = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
    return day_count / 360.0


def _thirty_e_360_fraction(start: date, end: date) -> float:
    """
    30E/360 Eurobond Basis day-count fraction.

    Adjusts both start and end day components:
    - If D1 = 31, set D1 = 30
    - If D2 = 31, set D2 = 30
    """
    d1 = min(start.day, 30)
    d2 = min(end.day, 30)
    m1 = start.month
    m2 = end.month
    y1 = start.year
    y2 = end.year

    day_count = 360 * (y2 - y1) + 30 * (m2 - m1) + (d2 - d1)
    return day_count / 360.0


def days_accrued(last_coupon_date: date, settlement_date: date,
                 convention: str) -> Tuple[int, float]:
    """
    Compute both actual days accrued and the day-count fraction.

    Parameters
    ----------
    last_coupon_date : date
        Previous coupon payment date
    settlement_date : date
        Trade settlement date
    convention : str
        Day-count convention

    Returns
    -------
    tuple of (int, float)
        Actual calendar days accrued and the day-count fraction
    """
    actual_days = _days_between(last_coupon_date, settlement_date)
    fraction = day_count_fraction(last_coupon_date, settlement_date, convention)
    return actual_days, fraction
