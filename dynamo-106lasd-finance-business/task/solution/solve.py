#!/usr/bin/env python3
"""Oracle: patches the 3 bugs in the multi-file engine."""
import sys
sys.path.insert(0, "/app")

# Fix 1: interest.py — use config.monthly_rate_fraction for day_count
with open("/app/interest.py") as f:
    code = f.read()
code = code.replace(
    "from config import rc, D",
    "from config import rc, D, monthly_rate_fraction"
)
code = code.replace(
    '    """Compute monthly interest for a loan."""\n'
    '    return rc(D(str(balance)) * rate_bps / 10000 / 12)',
    '    """Compute monthly interest for a loan."""\n'
    '    frac = monthly_rate_fraction(rate_bps, month, day_count)\n'
    '    return rc(D(str(balance)) * frac)'
)
with open("/app/interest.py", "w") as f:
    f.write(code)

# Fix 2: config.py — get_penalty_base returns current balance
with open("/app/config.py") as f:
    code = f.read()
code = code.replace(
    '    return loan["original_balance"]',
    '    return loan["balance"]'
)
with open("/app/config.py", "w") as f:
    f.write(code)

# Fix 3: engine.py — move loss allocation AFTER principal distribution
with open("/app/engine.py") as f:
    code = f.read()
# Remove loss allocation from before interest (Step 2 position)
code = code.replace(
    "        # Step 2: Loss allocation\n"
    "        loss_allocated = {t[\"name\"]: 0 for t in tranches}\n"
    "        for loss_amt in month_defaults:\n"
    "            allocated = allocate_losses(tranches, loss_amt)\n"
    "            for name, amt in allocated.items():\n"
    "                loss_allocated[name] += amt\n"
    "            cumulative_losses += loss_amt\n\n"
    "        # Step 3: Interest distribution",
    "        # Step 2: Interest distribution"
)
# Renumber Step 3->2, Step 4->3
code = code.replace("# Step 3: Interest distribution", "# Step 2: Interest distribution")
code = code.replace("# Step 4: Principal distribution", "# Step 3: Principal distribution")
# Insert loss allocation after principal, before residual
code = code.replace(
    "        # Step 5: Residual to equity",
    "        # Step 4: Loss allocation\n"
    "        loss_allocated = {t[\"name\"]: 0 for t in tranches}\n"
    "        for loss_amt in month_defaults:\n"
    "            allocated = allocate_losses(tranches, loss_amt)\n"
    "            for name, amt in allocated.items():\n"
    "                loss_allocated[name] += amt\n"
    "            cumulative_losses += loss_amt\n\n"
    "        # Step 5: Residual to equity"
)
with open("/app/engine.py", "w") as f:
    f.write(code)

# Run the fixed engine
exec(compile(open("/app/engine.py").read(), "/app/engine.py", "exec"))
