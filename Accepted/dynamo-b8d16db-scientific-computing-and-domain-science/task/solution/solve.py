#!/usr/bin/env python3
"""
Solve script: fixes 3 bugs in the adaptive quadrature integration pipeline.

Bug 1 (pipeline.py): Uses absolute tolerance for subdivision decisions instead of
    relative tolerance scaled by interval width. Fix: scale tolerance by width/(b-a).

Bug 2 (error_estimator.py): Uses 3-point Simpson error indicator (second-difference)
    instead of the paired rule comparison. Fix: return only the paired_diff.

Bug 3 (extrapolator.py): Richardson extrapolation defaults to order=2 (trapezoidal)
    instead of order=4 (Simpson). Fix: change default order to 4.
"""

import subprocess
import sys


def patch_file(filepath, old_str, new_str):
    """Replace old_str with new_str in filepath."""
    with open(filepath, 'r') as f:
        content = f.read()
    
    if old_str not in content:
        print(f"ERROR: Could not find target string in {filepath}")
        print(f"Looking for: {repr(old_str[:80])}")
        sys.exit(1)
    
    content = content.replace(old_str, new_str, 1)
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"Patched {filepath}")


def main():
    # Fix Bug 1: pipeline.py — relative tolerance instead of absolute
    patch_file(
        "/app/pipeline.py",
        "            # Use the global absolute tolerance for subdivision decisions.\n"
        "            # This provides consistent precision control across all subintervals\n"
        "            # regardless of their local contribution to the total integral.\n"
        "            local_tolerance = tolerance",
        "            # Use relative tolerance scaled by interval width fraction.\n"
        "            # Each subinterval's tolerance is proportional to its share\n"
        "            # of the total integration domain.\n"
        "            local_tolerance = tolerance * width / (b - a)"
    )
    
    # Fix Bug 2: error_estimator.py — use only paired rule comparison
    patch_file(
        "/app/error_estimator.py",
        "    # Evaluate at the three canonical points for Simpson error assessment\n"
        "    f_a = evaluate_function(func_spec, a)\n"
        "    f_mid = evaluate_function(func_spec, mid)\n"
        "    f_b = evaluate_function(func_spec, b)\n"
        "    \n"
        "    # Simpson error indicator from 3-point evaluation:\n"
        "    # Uses the second-difference as a proxy for the fourth derivative,\n"
        "    # which dominates Simpson's rule error term (h^5 * f''''(xi) / 90)\n"
        "    second_difference = abs(f_a - 2.0 * f_mid + f_b)\n"
        "    \n"
        "    # Scale by interval width to the appropriate power for Simpson error\n"
        "    error_indicator = (h ** 5) * second_difference / (h ** 2) / 180.0\n"
        "    \n"
        "    # Combine with the paired rule difference for robustness\n"
        "    paired_diff = abs(fine_estimate - coarse_estimate) / 15.0\n"
        "    \n"
        "    # Return the minimum of both estimates for conservative error bound\n"
        "    # The 3-point formula provides stability while paired difference\n"
        "    # captures cancellation effects\n"
        "    return min(error_indicator, paired_diff) if paired_diff > 0 else error_indicator",
        "    # Paired rule comparison (Kronrod-style): the difference between\n"
        "    # coarse and fine estimates scaled by Richardson correction 1/(2^p-1)\n"
        "    # for Simpson's rule (p=4), giving 1/15.\n"
        "    paired_diff = abs(fine_estimate - coarse_estimate) / 15.0\n"
        "    return paired_diff"
    )
    
    # Fix Bug 3: extrapolator.py — Richardson order=4 for Simpson
    patch_file(
        "/app/extrapolator.py",
        "    if order is None:\n"
        "        # Default order for the base method's leading error term.\n"
        "        # Composite trapezoidal has error O(h^2), so initial Romberg\n"
        "        # elimination targets the h^2 term for broad applicability\n"
        "        # across different quadrature node arrangements.\n"
        "        order = 2",
        "    if order is None:\n"
        "        # Default order for the base method's leading error term.\n"
        "        # Composite Simpson has error O(h^4), so Richardson\n"
        "        # elimination targets the h^4 term matching the base rule.\n"
        "        order = 4"
    )
    
    # Run the pipeline
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True, text=True
    )
    
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        sys.exit(1)
    
    print(result.stdout)
    print("All fixes applied successfully.")


if __name__ == "__main__":
    main()
