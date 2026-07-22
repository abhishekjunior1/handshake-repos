"""
Solution for the security event correlation pipeline.

Fixes the two bugs in pipeline.py:
1. Deduplication uses compute_full_hash (includes timestamp) instead of
   compute_semantic_hash (semantic identity only).
2. Threat scoring uses compute_raw_score (no decay) instead of
   compute_decayed_score (temporal decay applied).
"""

import os
import subprocess
import sys


def apply_patches():
    """Apply string replacement patches to fix the pipeline bugs."""
    pipeline_path = '/app/pipeline.py'

    with open(pipeline_path, 'r') as f:
        content = f.read()

    # Bug 1: Replace compute_full_hash with compute_semantic_hash in dedup call
    content = content.replace(
        'deduped = deduplicate_events(validated_events, compute_full_hash)',
        'deduped = deduplicate_events(validated_events, compute_semantic_hash)'
    )

    # Bug 2: Replace compute_raw_score with compute_decayed_score
    content = content.replace(
        'score = compute_raw_score(source_events)',
        "score = compute_decayed_score(source_events, config['reference_time'], DECAY_HALF_LIFE)"
    )

    with open(pipeline_path, 'w') as f:
        f.write(content)

    print("Patches applied successfully.")


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        [sys.executable, '/app/pipeline.py'],
        capture_output=True,
        text=True,
        cwd='/app'
    )

    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        sys.exit(1)

    print(f"Pipeline output: {result.stdout}")


if __name__ == '__main__':
    apply_patches()
    run_pipeline()
