"""
Oracle solution: patches bugs in the flow aggregation pipeline and runs it.
"""
import subprocess
import sys


def patch_pipeline():
    """Fix both bugs in pipeline.py."""
    filepath = "/app/pipeline.py"
    with open(filepath, "r") as f:
        content = f.read()

    # Fix Bug 1: population_size should use deduped count, not raw count
    content = content.replace(
        "            population_size=raw_count",
        "            population_size=len(deduped_flows)",
    )

    # Fix Bug 2: baseline update should use accumulate mode, not smoothed
    content = content.replace(
        "            mode='smoothed'",
        "            mode='accumulate'",
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
    patch_pipeline()
    run_pipeline()
