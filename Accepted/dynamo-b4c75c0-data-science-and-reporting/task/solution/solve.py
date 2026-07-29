"""
Solution: Fix two data-flow bugs in the pipeline orchestrator.

Bug 1: Pipeline passes full series length (n) to score_observations for
normalization instead of the effective sample size (n_effective) which
accounts for window function energy loss. With rectangular windows,
n_effective == n so the bug is invisible. With tapered windows (hann,
hamming, blackman), n_effective < n and scores are under-normalized.

Bug 2: Pipeline uses a global anomaly threshold for all segments instead
of computing per-segment thresholds. With a single-segment series (stationary),
global == segment-local. With multiple segments, each segment needs its own
threshold calibrated to local variance.
"""

import subprocess


def fix_pipeline():
    """Apply fixes to pipeline.py."""
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Fix Bug 1: Use n_effective instead of n for score normalization
    content = content.replace(
        '    # Score observations using their spectral residual contributions.\n'
        '    # The normalization denominator controls score scaling — use the full\n'
        '    # series length as the population size for density estimation. This\n'
        '    # provides scores in consistent units regardless of window choice.\n'
        '    scores = score_observations(whitened, spectral_residuals, n)',
        '    # Score observations using their spectral residual contributions.\n'
        '    # The normalization denominator accounts for the effective sample size\n'
        '    # after windowing — tapered windows reduce the effective degrees of\n'
        '    # freedom and scores must be normalized accordingly.\n'
        '    scores = score_observations(whitened, spectral_residuals, n_effective)'
    )

    # Fix Bug 2: Use per-segment thresholds instead of global
    content = content.replace(
        '        # Use the global series threshold for per-segment classification.\n'
        '        # This provides consistent detection sensitivity across segments —\n'
        '        # a segment-local threshold would adapt to local noise levels and\n'
        '        # mask anomalies in high-variance segments that are anomalous\n'
        '        # relative to the overall series behavior.\n'
        '        seg_threshold = global_threshold',
        '        # Compute segment-local threshold for adaptive detection sensitivity.\n'
        '        # Each segment has its own variance level and the threshold must\n'
        '        # reflect the local noise floor for proper anomaly calibration.\n'
        '        seg_threshold = compute_threshold(seg_data, anomaly_percentile)'
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)

    print("Applied 2 fixes to pipeline.py")


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        ['python3', '/app/pipeline.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode


if __name__ == '__main__':
    fix_pipeline()
    exit_code = run_pipeline()
    exit(exit_code)
