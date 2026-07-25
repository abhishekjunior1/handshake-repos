A Singular Spectrum Analysis (SSA) pipeline at `/app/pipeline.py` decomposes time series into trend, oscillatory, and noise components using trajectory matrix embedding and SVD. It uses modules `/app/embedder.py`, `/app/decomposer.py`, `/app/grouper.py`, `/app/reconstructor.py`, `/app/data_loader.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The pipeline produces correct output on the current configuration but has bugs that cause incorrect decomposition results on other inputs. Find and fix the bugs so the pipeline handles all valid configurations correctly.

Do not rewrite from scratch — preserve the existing module structure and computational methods.

The fixed pipeline will be tested on a different configuration than the one at `/app/config.json`.

Output: `/app/output.json` — JSON object with fields: `reconstructed_components` (list of reconstructed series per group), `contribution_ratios` (list of variance fractions per group), `eigenvalue_spectrum` (list of singular values), `w_correlation_matrix` (separability matrix between components), `residual_series` (original minus sum of reconstructions), and `diagnostics` (object with `trajectory_norm`, `effective_rank`, `trend_correlation`, `total_variance_explained`).
