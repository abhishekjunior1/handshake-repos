An A/B test experiment analysis pipeline at `/app/pipeline.py` processes experiment data through statistical analysis stages: loading observations, computing sample statistics, running hypothesis tests, applying multiple testing corrections, estimating statistical power, and generating a structured report. It uses modules `/app/data_loader.py`, `/app/statistics.py`, `/app/hypothesis_testing.py`, `/app/corrections.py`, `/app/power_analysis.py`, and `/app/reporting.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/experiment.json` and writes `/app/output.json`.

The pipeline produces correct output on the current experiment data but has bugs that cause incorrect results on experiments with different characteristics (multiple metrics, unequal group variances, small sample sizes). Find and fix the bugs so the pipeline handles all valid experiment configurations correctly.

Do not rewrite from scratch — preserve the existing module structure, the Welch's t-test implementation (appropriate for unequal variances), and the Hedges' g effect size with its finite-sample unbiasing factor (bias-corrected for small samples per Hedges & Olkin 1985). Power analysis reports power at the per-metric design alpha, not at a family-wise corrected threshold. The fixed pipeline will be tested on a different experiment than the one at `/app/experiment.json`.

Output: `/app/output.json` — a JSON report containing per-metric statistics and hypothesis test results, multiple testing correction results (adjusted p-values for ALL metrics), power analysis (using the appropriate reference variance), confidence intervals (using degrees of freedom appropriate for the variance structure), effect sizes, and an experiment summary.
