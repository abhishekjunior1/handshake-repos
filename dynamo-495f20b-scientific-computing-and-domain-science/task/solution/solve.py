"""
Solution: patches the two bugs in pipeline.py and runs the pipeline.

Bug 1: Shrinkage computation receives sigma_w_sq (within-group variance) where
it should receive tau_sq (between-group variance). The shrinkage factor formula
needs tau_sq to determine how much to pull group means toward the grand mean.

Bug 2: DIC computation uses n_groups (number of groups) as the effective
parameter count instead of model_fit["effective_parameters"] (the actual p_D
computed from shrinkage factors).
"""

import subprocess
import sys


def patch_pipeline():
    """Apply bug fixes to pipeline.py via string replacement."""
    with open("/app/pipeline.py", "r") as f:
        code = f.read()

    # Fix Bug 1: Pass tau_sq instead of sigma_w_sq as the between-group
    # variance argument to fit_hierarchical_model
    code = code.replace(
        "fit_hierarchical_model(\n"
        "        group_estimates, sigma_w_sq, sigma_w_sq, grand_mean\n"
        "    )",
        "fit_hierarchical_model(\n"
        "        group_estimates, sigma_w_sq, tau_sq, grand_mean\n"
        "    )",
    )

    # Fix Bug 2: Pass effective_parameters from the model fit instead of
    # n_groups for the DIC complexity penalty
    code = code.replace(
        'data["n_groups"],\n        data["total_observations"],',
        'model_fit["effective_parameters"],\n        data["total_observations"],',
    )

    with open("/app/pipeline.py", "w") as f:
        f.write(code)


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        ["python3", "/app/pipeline.py", "/app/observations.json", "/app/output.json"],
        cwd="/app",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
