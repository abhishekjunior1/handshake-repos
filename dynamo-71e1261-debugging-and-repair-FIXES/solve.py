"""Patches bugs in the flaky test diagnosis pipeline and runs on both evaluation configurations."""
import os
import subprocess
import sys

BASE_DIR = '/app'


def patch_file(filepath, old_str, new_str):
    """Apply a string replacement patch to a file."""
    with open(filepath, 'r') as f:
        content = f.read()
    if old_str not in content:
        print(f"ERROR: Patch target not found in {filepath}", file=sys.stderr)
        sys.exit(1)
    content = content.replace(old_str, new_str)
    with open(filepath, 'w') as f:
        f.write(content)


def fix_correlation_vectors():
    """Fix: Use unweighted binary vectors for correlation, not decay-weighted."""
    patch_file(
        os.path.join(BASE_DIR, 'pipeline.py'),
        'run_weighted_vectors, failing_test_ids, config["correlation_threshold"]',
        'binary_vectors, failing_test_ids, config["correlation_threshold"]'
    )


def fix_classifier_rate_stabilization():
    """Fix: Use provided rate directly, don't average with cumulative history."""
    patch_file(
        os.path.join(BASE_DIR, 'classifier.py'),
        """        # Use the provided rate directly for threshold comparison
        # Stabilize rate estimate by combining provided rate with cumulative history
        # to reduce sensitivity to transient window-level spikes that could
        # promote false-positive deterministic classification
        overall_rate = flaky_info.get("cumulative_failure_rate", rate)
        stabilized_rate = (rate + overall_rate) / 2.0""",
        '        stabilized_rate = rate'
    )


def run_pipeline(input_path, output_path):
    """Run the pipeline on a single input/output pair."""
    result = subprocess.run(
        [sys.executable, os.path.join(BASE_DIR, 'pipeline.py'), input_path, output_path],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed for {input_path}:\n{result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


def main():
    fix_correlation_vectors()
    fix_classifier_rate_stabilization()

    # Run on both evaluation configurations
    run_pipeline(
        os.path.join(BASE_DIR, 'eval_config_1.json'),
        os.path.join(BASE_DIR, 'output_eval_1.json')
    )
    run_pipeline(
        os.path.join(BASE_DIR, 'eval_config_2.json'),
        os.path.join(BASE_DIR, 'output_eval_2.json')
    )


if __name__ == '__main__':
    main()
