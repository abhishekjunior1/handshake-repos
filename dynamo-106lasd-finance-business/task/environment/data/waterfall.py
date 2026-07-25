"""Waterfall distribution logic for CDO tranches."""
from config import rc, D, PREPAY_PENALTY_RATE, get_penalty_base


def distribute_interest(tranches, available, turbo_active):
    """Pay interest pro-rata. Returns (interest_paid dict, remaining available, turbo_redirect)."""
    from interest import compute_tranche_coupon
    
    interest_owed = {}
    total_io = 0
    for t in tranches:
        if turbo_active and t["seniority"] == 2:
            interest_owed[t["name"]] = 0
        else:
            owed = compute_tranche_coupon(t["balance"], t["coupon_bps"])
            interest_owed[t["name"]] = owed
        total_io += interest_owed[t["name"]]

    interest_paid = {}
    if total_io <= available:
        for t in tranches:
            interest_paid[t["name"]] = interest_owed[t["name"]]
        available -= total_io
    else:
        for t in tranches:
            share = rc(available * interest_owed[t["name"]] / total_io) if total_io > 0 else 0
            interest_paid[t["name"]] = share
        available = 0

    # Turbo redirect: mezzanine's would-have-been coupon goes to available for principal
    turbo_redirect = 0
    if turbo_active:
        turbo_redirect = compute_tranche_coupon(tranches[1]["balance"], tranches[1]["coupon_bps"])

    return interest_paid, available, turbo_redirect


def distribute_principal(tranches, available):
    """Sequential principal distribution (senior-first)."""
    principal_paid = {t["name"]: 0 for t in tranches}
    for t in tranches:
        pay = min(available, t["balance"])
        principal_paid[t["name"]] = pay
        t["balance"] -= pay
        available -= pay
        if available == 0:
            break
    return principal_paid, available


def allocate_losses(tranches, loss_amount):
    """Allocate losses bottom-up through tranche stack."""
    loss_allocated = {t["name"]: 0 for t in tranches}
    remaining = D(str(loss_amount))
    for t in reversed(tranches):
        absorb = min(remaining, D(str(t["balance"])))
        absorb_r = rc(absorb)
        loss_allocated[t["name"]] += absorb_r
        t["balance"] -= absorb_r
        remaining -= absorb
        if remaining <= 0:
            break
    return loss_allocated


def compute_prepay_amount(loan, month):
    """Compute total prepayment: remaining balance + penalty if within lockout."""
    lockout = loan.get("lockout_months", 0)
    penalty = 0
    if month <= lockout:
        base = get_penalty_base(loan)
        penalty = rc(D(str(base)) * PREPAY_PENALTY_RATE)
    return loan["balance"] + penalty, penalty
