"""Fix the two bugs in pipeline.py.

Bug 1: score_decomposition uses n (full series length) instead of
    n_effective (effective DoF after windowing). With tapered windows,
    n_effective < n, and the SNR normalization must account for this.

Bug 2: Per-segment anomaly classification uses global_threshold for all
    segments instead of computing per-segment thresholds. With multiple
    regimes of different variance, the global threshold is inappropriate.
"""

import subprocess


def fix_pipeline():
    """Apply fixes to pipeline.py."""
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Bug 1: Change n to n_effective in score_decomposition call
    content = content.replace(
        'quality_scores = score_decomposition(residuals, total_harmonic_power, n)',
        'quality_scores = score_decomposition(residuals, total_harmonic_power, n_effective)'
    )

    # Bug 2: Replace global threshold with per-segment threshold
    # Change the threshold assignment inside the segment loop
    content = content.replace(
        '        seg_threshold = global_threshold',
        '        seg_threshold = compute_segment_threshold(seg_residuals, anomaly_percentile)'
    )

    # Add import for compute_segment_threshold
    content = content.replace(
        'from decomposition_scorer import (compute_segment_scores, detect_segments,\n                                  compute_global_threshold)',
        'from decomposition_scorer import (compute_segment_scores, detect_segments,\n                                  compute_global_threshold, compute_segment_threshold)'
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)


def main():
    fix_pipeline()
    result = subprocess.run(['python3', '/app/pipeline.py'],
                          capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        raise SystemExit(1)
    print(result.stdout)


if __name__ == '__main__':
    main()
