A metrics aggregation pipeline at `/app/pipeline.py` ingests raw counter, gauge, and histogram metrics from a JSON input file, computes per-second rates, percentile statistics, and downsampled rollups. It uses modules `/app/data_loader.py`, `/app/counter_processor.py`, `/app/gauge_processor.py`, `/app/histogram_processor.py`, `/app/rate_computer.py`, `/app/rollup_aggregator.py`, and `/app/output_formatter.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/metrics_input.json` and writes `/app/output.json`.

The pipeline produces correct output on the current metrics input but has bugs that cause incorrect results on other inputs with multiple sources, varying collection intervals, and larger time gaps between samples. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure and processing conventions. In particular, preserve the cross-source rate interleaving by timestamp (which ensures correct rollup bucket assignment when multiple sources contribute rates for the same counter) and the partial-bucket extrapolation for trailing gauge rollup windows (which ensures partial-window aggregates are comparable to full-window rollups). These are correct design decisions that must not be modified.

The individual modules (`counter_processor.py`, `gauge_processor.py`, `histogram_processor.py`, `rate_computer.py`, `rollup_aggregator.py`) implement their computations correctly. The bugs are in how `pipeline.py` orchestrates calls to these modules.

Output: `/app/output.json` — a JSON object with four top-level keys: `rates` (per-counter rate series with mean_rate and max_rate), `gauges` (per-gauge statistics with min, max, mean, last, count, stale_markers_inserted), `histograms` (per-histogram p50, p90, p95, p99, total_observations), and `rollups` (time-bucketed summaries for all metric types at 60-second intervals).
