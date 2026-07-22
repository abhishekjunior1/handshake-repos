A preconditioned conjugate gradient (PCG) solver pipeline at `/app/pipeline.py` solves sparse symmetric positive-definite linear systems. It uses modules `/app/problem_loader.py`, `/app/matrix_ops.py`, `/app/preconditioner.py`, `/app/pcg_solver.py`, `/app/convergence.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/problem_spec.json` and writes `/app/output.json`.

The pipeline produces correct output on the current input (a 2x2 diagonal system) but has bugs that cause incorrect results on larger coupled systems. Find and fix the bugs so the pipeline handles all valid SPD systems correctly.

Do not rewrite from scratch — preserve the existing module structure and PCG algorithm. The fixed pipeline will be tested on a different problem specification than the one at `/app/problem_spec.json`.

Output: `/app/output.json` — JSON object with keys: status, converged, iterations, dimension, tolerance_requested, solution (array of floats), residual_norms (array including initial), final_residual_norm, initial_residual_norm, relative_residual, condition_estimate, solver_metrics (efficiency, theoretical_iteration_bound, solution_norm, solution_max_component, solution_min_component), convergence_history (total_reduction, is_monotone, max_ratio, min_ratio, ratios).
