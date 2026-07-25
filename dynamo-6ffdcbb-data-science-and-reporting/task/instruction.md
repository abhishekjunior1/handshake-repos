A geostatistical analysis pipeline at `/app/pipeline.py` performs spatial interpolation using variogram estimation and ordinary kriging with leave-one-out cross-validation. It uses modules `/app/data_loader.py`, `/app/variogram.py`, `/app/kriging.py`, and `/app/cross_validation.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline loads spatial point data (x, y coordinates with measured values), estimates an experimental variogram by binning point-pair distances, fits a theoretical variogram model (spherical), uses the fitted model for ordinary kriging predictions via leave-one-out cross-validation, and reports model parameters alongside prediction accuracy statistics.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect results on other configurations. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and interfaces. The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`.

Output: `/app/output.json` — JSON with keys: `variogram_model` (nugget, sill, range, model_type), `experimental_variogram` (lag_distances, semivariance, n_pairs), `cross_validation` (predictions, variances, rmse, mean_error, mae, standardized_rmse, mean_standardized_error), and `metadata` (n_points, n_lags, max_lag).
