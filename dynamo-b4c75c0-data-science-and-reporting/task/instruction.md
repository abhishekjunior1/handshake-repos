A spectral anomaly detection pipeline at `/app/pipeline.py` identifies anomalous observations in time series using frequency-domain analysis. It uses modules `/app/periodogram.py`, `/app/spectral_model.py`, `/app/whitening.py`, `/app/anomaly_scorer.py`, and `/app/segment_analyzer.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/series_data.json` and writes `/app/output.json`.

The pipeline produces correct output on the current input data but has bugs that cause incorrect results on other time series configurations. Find and fix the bugs so the pipeline handles all valid inputs correctly, including non-stationary series with multiple variance regimes and non-rectangular window functions.

Do not rewrite from scratch — preserve the existing module structure, the temporal relevance weighting, and the angular frequency normalization. The fixed pipeline will be tested on a different time series configuration than the one at `/app/series_data.json`.

Output: `/app/output.json` — a JSON object with: `anomaly_scores` (list of per-observation scores in [0,1]), `overall_anomaly_score` (float), `total_anomalies` (integer), `segment_results` (list of dicts with start, end, mean_score, n_anomalies, anomaly_indices, threshold), `spectral_diagnostics` (dict with n_frequency_bins, total_spectral_energy, envelope_energy, unexplained_ratio, spectral_density_mean, n_effective), `whitening_diagnostics` (dict with whitened_variance, whitened_mean), and `parameters` (dict with window_type, envelope_order, anomaly_percentile, segment_min_length, n_observations, n_segments).
