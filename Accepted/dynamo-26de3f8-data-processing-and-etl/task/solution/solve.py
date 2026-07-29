"""
Oracle solution: patches bugs in the streaming pipeline and runs it.
"""
import subprocess
import sys


def patch_pipeline():
    """Fix both bugs in pipeline.py."""
    filepath = "/app/pipeline.py"
    with open(filepath, "r") as f:
        content = f.read()

    # Fix Bug 1: normalize should use deduped count, not raw count
    content = content.replace(
        "        normalized = normalize_window_results(\n"
        "            agg_result, raw_count, window_key, window_end\n"
        "        )",
        "        normalized = normalize_window_results(\n"
        "            agg_result, len(deduped_events), window_key, window_end\n"
        "        )",
    )

    # Fix Bug 2: carry-forward should not apply decay during accumulation
    content = content.replace(
        "        carry_forward_baseline = carry_forward_baseline + agg_result[\"window_sum\"] * decay_factor",
        "        carry_forward_baseline = carry_forward_baseline + agg_result[\"window_sum\"]",
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
