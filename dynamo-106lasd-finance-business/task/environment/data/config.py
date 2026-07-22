"""Configuration and helpers for the CDO cashflow engine."""
from decimal import Decimal, ROUND_HALF_UP

DAYS_IN_MONTH = {1: 31, 2: 28, 3: 31, 4: 30, 5: 31, 6: 30,
                 7: 31, 8: 31, 9: 30, 10: 31, 11: 30, 12: 31}

NUM_MONTHS = 12
TURBO_THRESHOLD_PCT = Decimal("0.05")
PREPAY_PENALTY_RATE = Decimal("0.02")

D = Decimal


def rc(v):
    """Round to nearest cent (half-up)."""
    return int(D(str(v)).quantize(D('1'), rounding=ROUND_HALF_UP))


def monthly_rate_fraction(rate_bps, month, day_count):
    """Return the monthly interest fraction for a given rate and day-count.

    For 30/360: rate_bps / 10000 / 12
    For actual/360: rate_bps / 10000 * days_in_month / 360
    """
    if day_count == "actual/360":
        days = DAYS_IN_MONTH.get(month, 30)
        return D(str(rate_bps)) / 10000 * days / 360
    return D(str(rate_bps)) / 10000 / 12


def get_penalty_base(loan):
    """Return the outstanding balance for prepayment penalty calculation."""
    return loan["original_balance"]
