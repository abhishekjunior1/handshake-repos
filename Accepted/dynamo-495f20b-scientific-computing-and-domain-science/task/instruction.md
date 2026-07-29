A Bayesian hierarchical model fitting pipeline at `/app/pipeline.py` loads grouped observation data, computes group-level estimates, fits an empirical Bayes shrinkage model (James-Stein), computes posterior credible intervals, calculates model comparison criteria (DIC, WAIC), and generates a structured report.

It uses modules `/app/data_loader.py`, `/app/group_estimator.py`, `/app/shrinkage_fitter.py`, `/app/interval_computer.py`, `/app/model_criteria.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/observations.json` and writes `/app/output.json`.

The pipeline produces correct output on the current observations but has bugs that cause incorrect results on other datasets. Find and fix the bugs so the pipeline handles all valid grouped observation data correctly, including datasets with varying group sizes and unequal within-group and between-group variances.

Do not rewrite from scratch — preserve the existing module structure and conventions. Preserve the James-Stein df adjustment, the t-distribution credible intervals, the harmonic-mean between-group variance estimator, and the WAIC summary-statistic computation path. The fixed pipeline will be tested on a different dataset than the one at `/app/observations.json`.

Output: `/app/output.json` — a JSON object with keys: `model_summary` (estimation method, group counts, effective parameters), `group_estimates` (per-group shrinkage factors, shrunken means, credible intervals), `variance_components` (within-group, between-group, ICC), `model_comparison` (DIC, WAIC, effective parameter counts), and `diagnostics` (shrinkage summaries, interval widths).
