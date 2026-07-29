An A/B test experiment analysis pipeline at `/app/pipeline.py` computes hypothesis tests, effect sizes, and statistical power for controlled experiments. It uses modules `/app/statistics_engine.py`, `/app/hypothesis_tests.py`, `/app/corrections.py`, `/app/effect_size.py`, and `/app/power_analysis.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct results on the current experiment configuration but has bugs that cause incorrect results on experiments with different characteristics. Find and fix the bugs so the pipeline handles all valid experiment configurations correctly, including multi-metric experiments with family-wise error control and experiments with unequal group variances.

Do not rewrite from scratch — preserve the existing module structure, the Welch's t-test choice, and the Hedges' g effect size formula. The fixed pipeline will be tested on a different experiment configuration than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with: `experiment_name` (string), `primary_metric` (dict with p_value, corrected_p_value, t_statistic, df, significant, significant_corrected), `secondary_metrics` (list of same-structure dicts), `effect_size` (dict with hedges_g, cohens_d, correction_factor), `confidence_interval` (dict with lower, upper, point_estimate), `power_analysis` (dict with observed_power, minimum_detectable_effect, power_target), `correction_info` (dict with method, n_tests, alpha_original), and `sample_summary` (dict with per-group n, mean, variance, and pooled_variance).
