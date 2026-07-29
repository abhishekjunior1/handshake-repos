A clinical survival analysis pipeline at `/app/pipeline.py` estimates Kaplan-Meier survival curves, runs log-rank tests, and fits a Cox proportional hazards model. It uses modules `/app/data_loader.py`, `/app/preprocessor.py`, `/app/kaplan_meier.py`, `/app/log_rank.py`, `/app/cox_model.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/cohort_data.json` and writes `/app/output.json`.

The pipeline produces correct output on the current cohort data but has bugs that cause incorrect statistical results on other datasets. Find and fix the bugs so the pipeline handles all valid survival data correctly.

Do not rewrite from scratch — preserve the existing module structure and statistical methods. The fixed pipeline will be tested on a different dataset than the one at `/app/cohort_data.json`.

Output: `/app/output.json` — a JSON object containing Kaplan-Meier survival estimates per group, log-rank test results, Cox model hazard ratios with concordance index, and analysis summary.
