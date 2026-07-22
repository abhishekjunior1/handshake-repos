"""Oracle solution: patches the bug in pipeline.py and runs the pipeline."""

import subprocess
import sys


def patch_pipeline():
    """Apply string replacement patch to fix the bug in pipeline.py."""
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # FIX: Spectral features must use the full averaged (corrected) PSD,
    # not just the last segment's PSD. The last segment can be
    # non-representative (e.g., due to non-stationarity or zero-padding).
    content = content.replace(
        "    # Extract spectral features from the most recent segment PSD to\n"
        "    # capture current spectral state rather than time-averaged behavior\n"
        "    current_psd = psd_list[-1] / (coherent_gain ** 2)\n"
        "    spectral_features = compute_spectral_features(freqs, current_psd)",
        "    # Extract spectral features from the averaged corrected PSD\n"
        "    spectral_features = compute_spectral_features(freqs, psd_corrected)"
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        [sys.executable, '/app/pipeline.py'],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    patch_pipeline()
    run_pipeline()
