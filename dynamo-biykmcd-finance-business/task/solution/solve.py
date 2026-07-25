"""
Solution for bond portfolio valuation pipeline.

Fixes three orchestrator bugs in pipeline.py:
1. Uses bond's own day_count_convention instead of hardcoded "ACT/360"
2. Uses bond's actual coupon_frequency instead of hardcoded annual (1)
3. Uses bond's settlement_days instead of hardcoded 0

After patching, re-runs the pipeline to produce correct output.
"""

import subprocess
import sys


def patch_pipeline():
    """Apply string-replacement patches to fix pipeline.py bugs."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, 'r') as f:
        content = f.read()

    # Fix Bug 1: Use bond's day_count_convention instead of hardcoded "ACT/360"
    content = content.replace(
        '        day_count_convention="ACT/360"',
        '        day_count_convention=day_count_convention'
    )

    # Fix Bug 2: Use bond's actual frequency instead of hardcoded 1
    content = content.replace(
        '        frequency=1',
        '        frequency=frequency'
    )

    # Fix Bug 3: Use bond's settlement_days instead of hardcoded 0
    content = content.replace(
        '    settlement_date = compute_settlement_date(valuation_date, 0)',
        '    settlement_date = compute_settlement_date(valuation_date, settlement_days)'
    )

    with open(pipeline_path, 'w') as f:
        f.write(content)


def run_pipeline():
    """Execute the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
