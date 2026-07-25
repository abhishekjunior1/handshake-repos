"""PLC Historian Migration Pipeline Fix.

Corrects two data-flow issues in pipeline.py:

1. Gap detection uses a fixed global threshold (5 seconds) for all tags
   regardless of their configured scan rate. Historian convention uses
   3× the tag's scan interval as the gap threshold — a 500ms scan rate
   tag should detect gaps at 1.5 seconds, not 5 seconds. This causes
   short gaps to be missed for fast-scanning tags.

2. Gap interpolation always uses linear mode for all tags. Discrete
   (boolean/state) tags require stepped interpolation (zero-order hold)
   because a discrete signal cannot take fractional intermediate values
   between state changes.
"""
import subprocess
import sys


def patch_pipeline():
    """Apply targeted string replacements to fix pipeline.py bugs."""
    pipeline_path = '/app/pipeline.py'

    with open(pipeline_path, 'r') as f:
        content = f.read()

    # Fix 1: Use tag-specific gap threshold based on scan_rate_us
    # The pipeline currently calls detect_gaps(samples) with no threshold,
    # using the default 5-second threshold for all tags. It should use
    # 3× the tag's scan rate when available (historian convention).
    content = content.replace(
        "    # Stage 3: Gap detection and interpolation\n"
        "    # Linear interpolation provides smooth value transitions across gaps\n"
        "    # for continuous process signals in the historian migration output\n"
        "    gaps = detect_gaps(samples)\n"
        "    if gaps:\n"
        "        samples = fill_gaps(samples, gaps, interpolation_mode='linear')",

        "    # Stage 3: Gap detection and interpolation\n"
        "    # Use tag-specific gap threshold based on scan rate when configured;\n"
        "    # historian convention is 3× scan interval for gap detection\n"
        "    scan_rate_us = tag_config.get('scan_rate_us', None)\n"
        "    if scan_rate_us:\n"
        "        gap_threshold = scan_rate_us * 3\n"
        "    else:\n"
        "        gap_threshold = DEFAULT_GAP_THRESHOLD_US\n"
        "    gaps = detect_gaps(samples, gap_threshold_us=gap_threshold)\n"
        "    if gaps:\n"
        "        # Discrete tags use stepped (zero-order hold) interpolation;\n"
        "        # analog tags use linear interpolation for smooth transitions\n"
        "        if tag_type == 'discrete':\n"
        "            interp_mode = 'stepped'\n"
        "        else:\n"
        "            interp_mode = 'linear'\n"
        "        samples = fill_gaps(samples, gaps, interpolation_mode=interp_mode)"
    )

    with open(pipeline_path, 'w') as f:
        f.write(content)

    print("Applied pipeline fixes:")
    print("  1. Gap threshold: uses 3× tag scan_rate_us (historian convention)")
    print("  2. Interpolation mode: stepped for discrete, linear for analog")


def run_pipeline():
    """Execute the patched pipeline."""
    result = subprocess.run(
        [sys.executable, '/app/pipeline.py'],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout, end='')


if __name__ == '__main__':
    patch_pipeline()
    run_pipeline()
