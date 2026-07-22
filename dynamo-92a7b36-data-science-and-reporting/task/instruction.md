A random-effects meta-analysis pipeline at `/app/pipeline.py` computes pooled effect estimates, heterogeneity statistics, publication bias tests, and prediction intervals. It uses modules `/app/data_loader.py`, `/app/heterogeneity.py`, `/app/egger_test.py`, `/app/random_effects.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/meta_data.json` and writes `/app/output.json`.

The pipeline produces correct output on the current study data but has bugs that cause incorrect statistical results on other datasets. Find and fix the bugs so the pipeline handles all valid meta-analysis data correctly.

Prediction intervals follow the Higgins & Thompson (2009) convention for degrees of freedom. Subgroup analyses estimate heterogeneity independently within each subgroup.

Do not rewrite from scratch — preserve the existing module structure and statistical methods. The fixed pipeline will be tested on a different dataset than the one at `/app/meta_data.json`.

Output: `/app/output.json` — a JSON object containing heterogeneity estimates, fixed-effect and random-effects pooled results, prediction intervals, Egger's test for publication bias, and subgroup analyses.
