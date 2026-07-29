A time-frequency feature extraction pipeline at `/app/pipeline.py` computes statistical and spectral features from multi-channel sensor signals. It uses modules `/app/time_features.py`, `/app/spectral_features.py`, `/app/correlation_features.py`, `/app/normalizer.py`, and `/app/windowing.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current sensor configuration but has bugs that cause incorrect results on signals with different characteristics. Find and fix the bugs so the pipeline handles all valid signal configurations correctly, including signals with linear trends, multi-window analysis with overlap, and reference baseline normalization.

Do not rewrite from scratch — preserve the existing module structure, the population kurtosis formula, and the 85% spectral rolloff threshold. The fixed pipeline will be tested on a different signal configuration than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with: `feature_vector` (dict of normalized feature values), `raw_features` (dict of pre-normalization values), `time_domain_summary` (dict per channel with rms, crest_factor, kurtosis), `spectral_summary` (dict per channel with spectral_centroid, spectral_bandwidth, spectral_rolloff), `cross_channel` (list of dicts with channel_pair, mean/max/min correlation), and `metadata` (dict with n_channels, n_samples, n_windows, window_size, overlap, sample_rate, rolloff_threshold, n_features).
