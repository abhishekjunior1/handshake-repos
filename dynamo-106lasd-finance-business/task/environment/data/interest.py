"""Interest computations for loans and tranches."""
from config import rc, D


def compute_loan_interest(balance, rate_bps, month, day_count):
    """Compute monthly interest for a loan."""
    return rc(D(str(balance)) * rate_bps / 10000 / 12)


def compute_tranche_coupon(balance, coupon_bps):
    """Compute monthly coupon for a tranche (always 30/360)."""
    return rc(D(str(balance)) * coupon_bps / 10000 / 12)
