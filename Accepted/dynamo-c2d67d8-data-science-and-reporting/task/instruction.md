A biostatistics analysis pipeline at `/app/pipeline.py` performs multi-group statistical comparisons with preprocessing, hypothesis testing, multiple comparison correction, and effect size computation. It uses modules `/app/data_loader.py`, `/app/preprocessor.py`, `/app/statistical_tests.py`, `/app/effect_size.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/study_data.json` and writes `/app/output.json`.

The pipeline produces correct output on the current study data but has bugs that cause incorrect statistical results on other datasets. Find and fix the bugs so the pipeline handles all valid inputs correctly, including small sample sizes and multiple comparisons.

Do not rewrite from scratch — preserve the existing module structure and statistical methods. The fixed pipeline will be tested on a different dataset than the one at `/app/study_data.json`.

Output: `/app/output.json` — a JSON object containing study metadata, summary statistics per group, outlier detection results, corrected hypothesis test results with effect sizes, and aggregated findings.
