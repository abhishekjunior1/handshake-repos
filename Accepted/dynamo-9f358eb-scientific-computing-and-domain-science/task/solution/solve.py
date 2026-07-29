"""Oracle solver: patches pipeline.py bugs and runs the fixed pipeline."""

import subprocess
import sys


def patch_pipeline():
    """Apply fixes to pipeline.py via string replacement."""
    with open("/app/pipeline.py", "r") as f:
        code = f.read()

    # Fix 1: Pass current_residual_norm instead of prev_norm to check_convergence
    code = code.replace(
        "converged = check_convergence(\n"
        "            prev_norm, initial_residual_norm, prev_norm, tol\n"
        "        )",
        "converged = check_convergence(\n"
        "            current_residual_norm, initial_residual_norm, prev_norm, tol\n"
        "        )",
    )

    # Fix 2: Pass only iteration norms (not initial) to estimate_condition_number
    code = code.replace(
        "cond_estimate = estimate_condition_number(residual_norms, iteration + 1)",
        "cond_estimate = estimate_condition_number(residual_norms[1:], iteration + 1)",
    )

    with open("/app/pipeline.py", "w") as f:
        f.write(code)


def main():
    patch_pipeline()
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)
    print(result.stdout)


if __name__ == "__main__":
    main()
