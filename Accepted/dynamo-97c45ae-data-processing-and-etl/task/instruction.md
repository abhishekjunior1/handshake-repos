A network flow aggregation pipeline at `/app/pipeline.py` deduplicates sampled flow observations, assigns them to time bins, and computes per-prefix traffic statistics with exponential smoothing. It uses modules `/app/flow_loader.py`, `/app/bin_assigner.py`, `/app/sampler.py`, `/app/traffic_calculator.py`, `/app/baseline_tracker.py`, and `/app/report_builder.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/flows.json` and writes `/app/output.json`.

The pipeline produces correct output on the current flow data but has bugs that cause incorrect results on other inputs. Find and fix the bugs so the pipeline handles all valid flow data correctly.

Do not rewrite from scratch — preserve the existing module structure and processing logic. The fixed pipeline will be tested on a different flow dataset than the one at `/app/flows.json`.

Output: `/app/output.json` — a JSON object containing per-bin traffic aggregation results with prefix-level statistics, smoothed utilization baselines, and deduplication summary.
