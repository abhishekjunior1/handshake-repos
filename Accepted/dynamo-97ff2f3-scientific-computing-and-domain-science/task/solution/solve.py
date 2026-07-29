"""
Oracle solution: patches all bugs in the ODE solver pipeline and runs it.
"""

import subprocess
import sys


def patch_rk_methods():
    """Fix Bug 1: compute_embedded_error uses only atol, missing rtol scaling."""
    filepath = "/app/rk_methods.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy code uses only atol as the scale factor:
    #     scale = atol
    # Fix: use the mixed tolerance scale as documented:
    #     scale = atol + rtol * max(|y_i|, |y_new_i|)
    old_code = """    sum_sq = 0.0
    for i in range(n):
        # Scale factor for this component
        scale = atol
        err_scaled = y_err[i] / scale if scale > 0 else 0.0
        sum_sq += err_scaled ** 2"""

    new_code = """    sum_sq = 0.0
    for i in range(n):
        # Scale factor: mixed absolute and relative tolerance
        scale = atol + rtol * max(abs(y[i]), abs(y_new[i]))
        err_scaled = y_err[i] / scale if scale > 0 else 0.0
        sum_sq += err_scaled ** 2"""

    content = content.replace(old_code, new_code)

    with open(filepath, "w") as f:
        f.write(content)


def patch_step_controller():
    """Fix Bug 2: step size exponent uses 1/4 instead of 1/5 for RK45."""
    filepath = "/app/step_controller.py"
    with open(filepath, "r") as f:
        content = f.read()

    content = content.replace(
        "    error_order = 4\n    return 1.0 / error_order",
        "    error_order = 5\n    return 1.0 / error_order",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_stiffness_detector():
    """Fix Bug 3: stiffness evaluation comparison is inverted."""
    filepath = "/app/stiffness_detector.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy code returns True when ratio < threshold (non-stiff looks stiff)
    # Fix: return True when ratio > threshold (stiff systems detected)
    content = content.replace(
        "        return stiffness_ratio < self.threshold",
        "        return stiffness_ratio > self.threshold",
    )
    content = content.replace(
        "    return stiffness_ratio < threshold",
        "    return stiffness_ratio > threshold",
    )

    with open(filepath, "w") as f:
        f.write(content)


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


if __name__ == "__main__":
    patch_rk_methods()
    patch_step_controller()
    patch_stiffness_detector()
    run_pipeline()
