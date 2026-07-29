"""Oracle solution - patches the 2 bugs in the spectral anomaly pipeline."""

import subprocess


def patch_file(filepath, old, new):
    """Replace exact string in file."""
    with open(filepath, 'r') as f:
        content = f.read()
    assert old in content, f"Patch target not found in {filepath}: {repr(old[:80])}"
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)


def main():
    # Bug 1 Fix: Use window-adjusted n_effective instead of full series length
    patch_file(
        '/app/pipeline.py',
        "        # Use full series length as population size for density estimation\n"
        "        score_result = compute_anomaly_scores(\n"
        "            whitened['residuals'], n_effective=n, decay_rate=decay_rate\n"
        "        )",
        "        # Use window-adjusted effective sample size for proper scaling\n"
        "        score_result = compute_anomaly_scores(\n"
        "            whitened['residuals'], n_effective=spectral['n_effective'], decay_rate=decay_rate\n"
        "        )"
    )

    # Bug 2 Fix: Use per-segment local thresholds instead of global threshold
    patch_file(
        '/app/pipeline.py',
        "    # Step 5: Apply global threshold for consistent detection\n"
        "    global_threshold = compute_threshold(global_scores, confidence=confidence)\n"
        "\n"
        "    # Classify anomalies using global threshold\n"
        "    classified_segments = []\n"
        "    for seg_idx, scores in enumerate(all_segment_results):\n"
        "        if not scores:\n"
        "            classified_segments.append([])\n"
        "            continue\n"
        "        classified = classify_anomalies(scores, global_threshold)\n"
        "        classified_segments.append(classified)\n"
        "\n"
        "        # Update segment stats with anomaly count\n"
        "        seg_stats[seg_idx]['n_anomalies'] = sum(\n"
        "            1 for c in classified if c['is_anomaly']\n"
        "        )\n"
        "        seg_stats[seg_idx]['threshold'] = global_threshold",
        "    # Step 5: Apply segment-local thresholds for adaptive detection\n"
        "    classified_segments = []\n"
        "    for seg_idx, scores in enumerate(all_segment_results):\n"
        "        if not scores:\n"
        "            classified_segments.append([])\n"
        "            continue\n"
        "        local_threshold = compute_threshold(scores, confidence=confidence)\n"
        "        classified = classify_anomalies(scores, local_threshold)\n"
        "        classified_segments.append(classified)\n"
        "\n"
        "        # Update segment stats with anomaly count\n"
        "        seg_stats[seg_idx]['n_anomalies'] = sum(\n"
        "            1 for c in classified if c['is_anomaly']\n"
        "        )\n"
        "        seg_stats[seg_idx]['threshold'] = local_threshold"
    )

    # Run the fixed pipeline
    subprocess.run(['python3', '/app/pipeline.py'], check=True)


if __name__ == '__main__':
    main()
