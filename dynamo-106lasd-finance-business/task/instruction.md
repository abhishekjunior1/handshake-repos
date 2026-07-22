A CDO cashflow engine at `/app/engine.py` computes monthly tranche distributions from a loan pool. It uses helper modules `/app/config.py`, `/app/interest.py`, and `/app/waterfall.py`.

Run it with `python3 /app/engine.py`. It reads `/app/pool.json` and `/app/tranches.json`, writes `/app/distributions.json`.

The engine produces correct output for the current pool but has bugs that cause incorrect distributions on other pool configurations. Find and fix the bugs so the engine handles all valid pools correctly.

Do not rewrite from scratch — the existing architecture and module boundaries must be preserved. The fixed engine will be tested on a different pool than the one at `/app/pool.json`.

Output: `/app/distributions.json` — JSON array of 12 months, each with `month` and `tranches` (keyed by name) containing `interest_paid`, `principal_paid`, `loss_allocated`, `ending_balance`. All amounts in integer cents.
