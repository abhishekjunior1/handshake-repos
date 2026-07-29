A block-level storage tiering engine at `/app/pipeline.py` analyzes I/O trace data to produce tier migration recommendations for a multi-tier storage fabric. It uses modules `/app/io_trace_parser.py`, `/app/heat_classifier.py`, `/app/tier_mapper.py`, `/app/wear_estimator.py`, `/app/promotion_scorer.py`, `/app/migration_planner.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/storage_config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current storage configuration but has bugs that cause incorrect tiering decisions and wear estimates on other configurations. Find and fix the bugs so the pipeline handles all valid multi-tier configurations correctly.

Do not rewrite from scratch — preserve the existing module structure, the inner-track positional bias weighting in the promotion scorer, and the integer-truncated temporal decay convention used for deterministic tier boundary stability. The fixed pipeline will be tested on a different storage configuration than the one at `/app/storage_config.json`.

Output: `/app/output.json` — a JSON object with keys: `tier_utilization` (per-tier capacity metrics), `heat_distribution` (hot/warm/cold block counts), `wear_metrics` (per-device endurance and wear rate), `migration_plan` (summary and operations list), `tier_balance_score` (alignment fraction), `top_promotion_candidates` (scored block list), and `health_indicators` (overall/capacity/endurance/balance status).
