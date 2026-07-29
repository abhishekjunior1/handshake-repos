A flaky test diagnosis pipeline at `/app/pipeline.py` analyzes test execution history across multiple runs to classify failing tests as deterministic bugs, flaky tests, or environment-dependent failures. It uses modules `/app/timing_analyzer.py`, `/app/correlation_analyzer.py`, `/app/flakiness_detector.py`, `/app/classifier.py`, `/app/confidence_scorer.py`, and `/app/report_generator.py`.

The pipeline produces correct diagnostic reports on the current test execution history but has bugs that cause incorrect classifications and correlation analysis on other execution histories. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure and analysis methods.

**Behavioral contract:** The correlation analysis uses single decay-weighting — the binary failure vectors are passed directly to the correlation module, which applies its own internal temporal decay weighting.

The fixed pipeline will be tested on different execution histories than the one at `/app/input_data.json`.

Output format: a JSON object with keys: `suite` (string), `analysis_summary` (object with total_tests, total_runs, tests_with_failures), `classifications` (array of objects each with test_id, category, confidence, metrics, correlated_tests, windowed_rates, trend), `correlation_matrix` (object mapping test pairs to correlation values), `timing_baselines` (object mapping module names to timing statistics), `overall_health` (object with healthy_pct, flaky_pct, deterministic_pct, env_dependent_pct).

After fixing all bugs, run the pipeline on the evaluation configurations:

```
python3 /app/pipeline.py /app/eval_config_1.json /app/output_eval_1.json
python3 /app/pipeline.py /app/eval_config_2.json /app/output_eval_2.json
```

You have 3600 seconds to complete this task. Do not cheat by using online solutions or hints specific to this task.
