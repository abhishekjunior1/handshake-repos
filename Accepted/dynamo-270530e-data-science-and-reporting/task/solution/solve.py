#!/usr/bin/env python3
"""
Solution script for SSA pipeline.
Patches the two bugs and runs the pipeline to produce correct output.
"""

import os
import subprocess
import sys


def patch_file(filepath, old_string, new_string):
    """Replace old_string with new_string in filepath."""
    with open(filepath, 'r') as f:
        content = f.read()

    if old_string not in content:
        print(f"ERROR: Could not find patch target in {filepath}")
        print(f"Looking for: {repr(old_string[:100])}")
        sys.exit(1)

    content = content.replace(old_string, new_string, 1)

    with open(filepath, 'w') as f:
        f.write(content)

    print(f"Patched: {filepath}")


def main():
    app_dir = '/app'
    if not os.path.exists(os.path.join(app_dir, 'pipeline.py')):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        candidate = os.path.join(script_dir, '..', 'environment', 'data')
        if os.path.exists(os.path.join(candidate, 'pipeline.py')):
            app_dir = os.path.abspath(candidate)
        else:
            app_dir = os.getcwd()

    pipeline_path = os.path.join(app_dir, 'pipeline.py')
    grouper_path = os.path.join(app_dir, 'grouper.py')

    # Fix Bug 1 (pipeline.py): Pass L, K in correct order to reconstruct_groups
    patch_file(
        pipeline_path,
        '    # Pass trajectory dimensions in column-major order for reconstruction\n'
        '    # alignment with the SVD factorization convention (V spans columns)\n'
        '    reconstructed_components = reconstruct_groups(grouped_matrices, N, K, L)',
        '    # Reconstruct with correct dimension ordering\n'
        '    reconstructed_components = reconstruct_groups(grouped_matrices, N, L, K)'
    )

    # Fix Bug 2 (grouper.py): Use weights (singular values) not weights**2 (eigenvalues)
    patch_file(
        grouper_path,
        '    # Eigenvalue weighting for variance-proportional correlation structure\n'
        '    weighted_norms = np.zeros(n, dtype=np.float64)\n'
        '    for i in range(n):\n'
        '        Xi = component_matrices[i]\n'
        '        # Use weights**2 (eigenvalues) for variance-proportional scaling\n'
        '        norm_sq = np.sum(Xi * Xi * W) * (weights[i] ** 2 if i < len(weights) else 1.0)',
        '    # Singular value weighting for proper SSA w-correlation\n'
        '    weighted_norms = np.zeros(n, dtype=np.float64)\n'
        '    for i in range(n):\n'
        '        Xi = component_matrices[i]\n'
        '        # Use singular values for proper w-correlation weighting\n'
        '        norm_sq = np.sum(Xi * Xi * W) * (weights[i] if i < len(weights) else 1.0)'
    )

    # Run the fixed pipeline
    print("\nRunning fixed pipeline...")
    result = subprocess.run(
        [sys.executable, os.path.join(app_dir, 'pipeline.py')],
        cwd=app_dir,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}")
        print(f"Stdout: {result.stdout}")
        sys.exit(1)

    print(result.stdout)
    print("Solution applied successfully.")


if __name__ == '__main__':
    main()
