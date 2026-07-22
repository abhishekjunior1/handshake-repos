A weighted hierarchical rollup pipeline at `/app/pipeline.py` processes sales transaction data through temporal weighting, contribution scoring, outlier detection, hierarchical aggregation, and normalization. The pipeline uses these modules:

- `/app/temporal_weighter.py` — applies exponential decay weights based on transaction age relative to a reference date, using a configurable half-life parameter
- `/app/contribution_scorer.py` — computes each record's weighted contribution within its group and normalizes scores using min-max scaling
- `/app/outlier_detector.py` — identifies statistical outliers using modified Z-scores based on MAD (Median Absolute Deviation) and clamps extreme values
- `/app/hierarchy_aggregator.py` — performs bottom-up rollup from product level through category to department using weighted aggregation
- `/app/normalizer.py` — computes cross-group percentage shares with dampening normalization
- `/app/output_formatter.py` — formats the multi-level rollup results into structured JSON output

Run it with `python3 /app/pipeline.py input.json output.json`. It reads `/app/input.json` and writes `/app/output.json`.

The pipeline produces correct output on the current input data but has bugs that cause incorrect results on other inputs. The current input happens to create degenerate conditions where the bugs are masked. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure. Preserve the dampening normalization function and the harmonic mean recency scoring. These are correct and must remain unchanged.

The fixed pipeline will be tested on a different input than the one at `/app/input.json`. The test input has multiple categories with varying transaction ages and includes outlier values.

Output: `/app/output.json` — a JSON object with fields: `format_version`, `pipeline` (name, version, parameters), `input_summary` (record_count, date_range, hierarchy_validation, recency_score, weight_statistics), `results` (product/category/department level records with revenue, weights, scores, shares), and `diagnostics` (outlier_detection, contribution_statistics, rollup_summary, normalization).
