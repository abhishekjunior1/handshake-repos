A model evaluation pipeline at `/app/pipeline.py` computes classification metrics, ROC-AUC, probability calibration, and cross-validation scores for a multiclass classifier. It uses modules `/app/data_loader.py`, `/app/metrics.py`, `/app/roc_auc.py`, `/app/calibration.py`, `/app/cross_validation.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/eval_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current evaluation configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid evaluation configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and evaluation methodology. The fixed pipeline will be tested on a different evaluation configuration than the one at `/app/eval_config.json`.

Output: `/app/output.json` — a JSON object with sections: `evaluation_metadata` (mode, classes, sample count), `classification_report` (per-class precision/recall/F1, macro F1, weighted F1, accuracy), `roc_auc` (per-class and macro AUC), `calibration` (ECE, MCE, bin count, positive class), and `cross_validation` (mean/std weighted F1, per-fold scores, fold count).
