"""
Solution: Fix three data-flow bugs in the feature extraction pipeline.

Bug 1: Cross-channel correlations computed on raw signals instead of detrended.
Bug 2: Normalization always self-computes baseline, ignoring reference stats.
Bug 3: Window count reported using overlap=0 instead of actual overlap.
"""

import subprocess


def fix_pipeline():
    """Apply fixes to pipeline.py."""
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Fix Bug 1: Detrend signals before cross-correlation
    content = content.replace(
        '    # Use the raw signal directly for correlation — this captures the\n'
        '    # full signal structure including any deterministic trends that\n'
        '    # indicate systematic inter-channel relationships.\n'
        '    cross_features = []\n'
        '    for i in range(n_channels):\n'
        '        for j in range(i + 1, n_channels):\n'
        '            ch_a = channels[i]\n'
        '            ch_b = channels[j]\n'
        '\n'
        '            # Correlate full raw signals for each window pair\n'
        '            pair_correlations = []\n'
        '            for w_idx in range(len(windows_per_channel[ch_a])):\n'
        '                sig_a = windows_per_channel[ch_a][w_idx]\n'
        '                sig_b = windows_per_channel[ch_b][w_idx]\n'
        '                corr = compute_cross_correlation(sig_a, sig_b)\n'
        '                pair_correlations.append(corr)',
        '    # Detrend signals before correlation to isolate dynamic coupling\n'
        '    # from static trend relationships between channels.\n'
        '    cross_features = []\n'
        '    for i in range(n_channels):\n'
        '        for j in range(i + 1, n_channels):\n'
        '            ch_a = channels[i]\n'
        '            ch_b = channels[j]\n'
        '\n'
        '            # Correlate detrended signals for each window pair\n'
        '            pair_correlations = []\n'
        '            for w_idx in range(len(windows_per_channel[ch_a])):\n'
        '                sig_a = detrend_signal(windows_per_channel[ch_a][w_idx])\n'
        '                sig_b = detrend_signal(windows_per_channel[ch_b][w_idx])\n'
        '                corr = compute_cross_correlation(sig_a, sig_b)\n'
        '                pair_correlations.append(corr)'
    )

    # Add import for detrend_signal if not already imported
    if 'from correlation_features import compute_cross_correlation' in content:
        content = content.replace(
            'from correlation_features import compute_cross_correlation',
            'from correlation_features import compute_cross_correlation, detrend_signal'
        )

    # Fix Bug 2: Use reference baseline when available
    content = content.replace(
        '    # Compute normalization baseline from current batch statistics.\n'
        '    # Using external reference baselines from config introduces a stale-reference\n'
        '    # hazard: if the machine\'s operating envelope changes (bearing wear, load\n'
        '    # redistribution, seasonal thermal drift), the historical reference becomes\n'
        '    # invalid and normalized features drift toward saturation. Self-relative\n'
        '    # normalization adapts intrinsically to the current operating regime,\n'
        '    # ensuring the feature vector always represents relative deviation from\n'
        '    # the present condition rather than deviation from a potentially obsolete\n'
        '    # reference point.\n'
        '    baseline_stats = compute_baseline_stats(feature_vector)',
        '    # Use reference baseline when available, fall back to self-computed\n'
        '    if baseline_config:\n'
        '        baseline_stats = baseline_config\n'
        '    else:\n'
        '        baseline_stats = compute_baseline_stats(feature_vector)'
    )

    # Fix Bug 3: Use actual overlap for window count
    content = content.replace(
        '    # Report window count using non-overlapping segment count for\n'
        '    # interpretable feature density — each non-overlapping segment\n'
        '    # represents an independent observation unit\n'
        '    n_windows = compute_window_count(n_samples, window_size, overlap=0)',
        '    # Report actual window count with configured overlap\n'
        '    n_windows = compute_window_count(n_samples, window_size, overlap)'
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)

    print("Applied 3 fixes to pipeline.py")


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
