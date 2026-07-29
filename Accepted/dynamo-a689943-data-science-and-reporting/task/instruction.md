A spectral anomaly detection pipeline at `/app/pipeline.py` identifies anomalous observations in time series data using frequency-domain methods. It uses modules `/app/spectral_estimator.py`, `/app/ar_model.py`, `/app/whitening.py`, `/app/segmenter.py`, `/app/scorer.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline performs: variance-based segmentation of non-stationary series, periodogram spectral density estimation with configurable window functions, AR spectral envelope fitting via Levinson-Durbin recursion, Nadaraya-Watson kernel smoothing for spectral whitening, per-observation anomaly scoring with temporal decay weighting, and threshold-based anomaly classification.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid inputs correctly, including non-stationary series with multiple variance regimes and tapered window functions.

Do not rewrite from scratch — preserve the existing module structure and interfaces. The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with keys:
- `summary`: total_observations, n_anomalies, anomaly_rate, n_segments, mean_severity, max_severity
- `segments`: per-segment metadata including start, end, length, mean, variance, n_anomalies, threshold
- `anomalies`: list of detected anomalies with global_index, segment, score, threshold, severity
- `spectral`: per-segment spectral analysis metadata
- `config`: pipeline configuration parameters used

Scoring conventions: anomaly scores are normalized by the effective sample size (which accounts for window energy loss). Thresholds are computed per-segment from the local score distribution at the configured confidence level.
