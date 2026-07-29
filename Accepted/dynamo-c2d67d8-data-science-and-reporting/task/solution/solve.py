"""
Oracle solution: patches all bugs in the biostatistics pipeline and runs it.
"""

import re
import subprocess
import sys


def patch_preprocessor():
    """Fix Bug 1: winsorize_data uses n instead of (n-1) for percentile positions."""
    filepath = "/app/preprocessor.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy lines use n * (percentile / 100.0) for lower and upper index
    # Fix: use (n - 1) * (percentile / 100.0) which is the linear interpolation method
    content = content.replace(
        "lower_idx = n * (percentile / 100.0)",
        "lower_idx = (n - 1) * (percentile / 100.0)",
    )
    content = content.replace(
        "upper_idx = n * ((100.0 - percentile) / 100.0)",
        "upper_idx = (n - 1) * ((100.0 - percentile) / 100.0)",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_statistical_tests():
    """Fix Bug 2: Holm-Bonferroni sorts descending instead of ascending."""
    filepath = "/app/statistical_tests.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy line sorts p-values in descending order (reverse=True)
    # Fix: sort ascending (reverse=False) for proper step-down procedure
    content = content.replace(
        "indexed.sort(key=lambda x: x[1], reverse=True)",
        "indexed.sort(key=lambda x: x[1], reverse=False)",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_effect_size():
    """Fix Bug 3: Cohen's d uses (n_a + n_b) instead of (n_a + n_b - 2)."""
    filepath = "/app/effect_size.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy line divides by (n_a + n_b) for pooled variance
    # Fix: divide by (n_a + n_b - 2) for unbiased pooled variance estimate
    content = content.replace(
        "pooled_var = (ss_a + ss_b) / (n_a + n_b)",
        "pooled_var = (ss_a + ss_b) / (n_a + n_b - 2)",
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
    patch_preprocessor()
    patch_statistical_tests()
    patch_effect_size()
    run_pipeline()
