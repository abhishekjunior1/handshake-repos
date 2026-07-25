An adaptive quadrature integration pipeline at `/app/pipeline.py` computes definite integrals using composite Simpson quadrature with error estimation, Richardson extrapolation for convergence acceleration, and singularity handling for algebraic endpoint singularities. It uses modules `/app/quadrature.py`, `/app/error_estimator.py`, `/app/extrapolator.py`, `/app/subdivider.py`, `/app/singularity_handler.py`, and `/app/utils.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/input.json` and writes `/app/output.json`.

The pipeline produces correct output on the current input but has bugs that cause incorrect results on other inputs. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure. In particular, preserve the 1/3-2/3 anti-resonance subdivision strategy (which prevents aliasing with periodic integrands per de Boor's CADRE algorithm) and the power-law endpoint transformation for algebraic singularities (which regularizes integrands with endpoint singularity strength 0 < alpha < 1).

The pipeline uses the following numerical conventions: error estimation uses paired rule comparison (the scaled difference between coarse and fine quadrature approximations, with Richardson correction factor 1/15 for Simpson's rule); Richardson extrapolation uses the method order matching the base quadrature rule (order p=4 for composite Simpson); subdivision tolerance is relative to interval width (each subinterval's tolerance is proportional to its fraction of the total integration domain).

The fixed pipeline will be tested on a different input than the one at `/app/input.json`.

Output: `/app/output.json` — a JSON object with fields: `integral_value` (the computed integral as a float), `error_estimate` (estimated absolute error), `subdivisions` (number of adaptive subdivision steps performed), `convergence_order` (observed order of convergence from the refinement sequence), `singularity_strength` (detected algebraic singularity exponent, 0.0 if none), and `method_info` (dict with method name and diagnostic details).
