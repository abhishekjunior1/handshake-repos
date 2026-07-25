"""CDO cashflow engine — orchestrates monthly waterfall distributions."""
import json

from config import rc, D, NUM_MONTHS, TURBO_THRESHOLD_PCT
from interest import compute_loan_interest
from waterfall import (distribute_interest, distribute_principal,
                       allocate_losses, compute_prepay_amount)


def run(pool_path="/app/pool.json", tranches_path="/app/tranches.json",
        output_path="/app/distributions.json"):
    pool = json.load(open(pool_path))
    tranches_def = json.load(open(tranches_path))

    loans = []
    for l in pool:
        loans.append({
            "id": l["loan_id"], "balance": l["original_balance"],
            "original_balance": l["original_balance"],
            "payment": l["scheduled_payment"], "rate_bps": l["rate_bps"],
            "recovery_rate": l["recovery_rate"],
            "default_month": l["default_month"],
            "prepay_month": l.get("prepay_month"),
            "lockout_months": l.get("lockout_months", 0),
            "day_count": l.get("day_count", "30/360"),
            "defaulted": False, "retired": False
        })

    tranches = sorted([{"name": t["name"], "balance": t["balance"],
                        "coupon_bps": t["coupon_bps"], "seniority": t["seniority"]}
                       for t in tranches_def], key=lambda x: x["seniority"])

    orig_pool_balance = sum(l["original_balance"] for l in loans)
    turbo_threshold = rc(D(str(orig_pool_balance)) * TURBO_THRESHOLD_PCT)
    cumulative_losses = 0
    turbo_active = False

    distributions = []
    for month in range(1, NUM_MONTHS + 1):
        available = 0
        month_defaults = []

        # Step 1: Collect payments
        for loan in loans:
            if loan["defaulted"] or loan["retired"]:
                continue
            if loan["default_month"] == month:
                loan["defaulted"] = True
                loss_amt = rc(D(str(loan["balance"])) * (1 - D(str(loan["recovery_rate"]))))
                month_defaults.append(loss_amt)
                continue
            if loan["prepay_month"] == month:
                prepay_total, _ = compute_prepay_amount(loan, month)
                available += prepay_total
                loan["balance"] = 0
                loan["retired"] = True
                continue
            ip = compute_loan_interest(loan["balance"], loan["rate_bps"],
                                       month, loan["day_count"])
            pp = loan["payment"] - ip
            loan["balance"] = max(0, loan["balance"] - pp)
            available += loan["payment"]

        # Step 2: Loss allocation
        loss_allocated = {t["name"]: 0 for t in tranches}
        for loss_amt in month_defaults:
            allocated = allocate_losses(tranches, loss_amt)
            for name, amt in allocated.items():
                loss_allocated[name] += amt
            cumulative_losses += loss_amt

        # Step 3: Interest distribution
        interest_paid, available, turbo_redirect = distribute_interest(
            tranches, available, turbo_active)

        # Step 4: Principal distribution
        available += turbo_redirect
        principal_paid, available = distribute_principal(tranches, available)

        # Step 5: Residual to equity
        if available > 0:
            for t in tranches:
                if t["seniority"] == 3:
                    principal_paid[t["name"]] += available
                    available = 0
                    break

        # Step 6: Turbo trigger (activates when losses strictly exceed threshold)
        if not turbo_active and cumulative_losses > turbo_threshold:
            turbo_active = True

        month_data = {}
        for t in tranches:
            month_data[t["name"]] = {
                "interest_paid": interest_paid[t["name"]],
                "principal_paid": principal_paid[t["name"]],
                "loss_allocated": loss_allocated[t["name"]],
                "ending_balance": t["balance"]
            }
        distributions.append({"month": month, "tranches": month_data})

    json.dump(distributions, open(output_path, "w"), indent=2)
    print(f"Wrote {len(distributions)} months")


if __name__ == "__main__":
    run()
