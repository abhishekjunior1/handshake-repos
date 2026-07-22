"""Solution for A/B experiment analysis pipeline.

Patches two bugs in pipeline.py:
1. Power analysis incorrectly uses Bonferroni-adjusted alpha (alpha/num_comparisons)
   instead of the raw per-metric alpha for power computation
2. Confidence interval uses treatment variance for both groups instead of
   each group's own variance
"""

import subprocess
import sys


def apply_fixes():
    """Apply all bug fixes to pipeline.py via string replacement."""
    pipeline_path = "/app/pipeline.py"
    
    with open(pipeline_path, 'r') as f:
        code = f.read()
    
    # Fix 1: Use raw alpha instead of Bonferroni-adjusted alpha for power
    code = code.replace(
        '    # Use Bonferroni-adjusted alpha for family-wise power computation\n'
        '    # to maintain consistency with the correction applied to p-values\n'
        '    power_alpha = primary_metric["alpha"] / num_comparisons',
        '    # Use the per-metric significance level for power computation\n'
        '    power_alpha = primary_metric["alpha"]'
    )
    
    # Fix 2: Use control variance for control term in SE calculation
    code = code.replace(
        '    # Standard error using treatment variance as the reference precision\n'
        '    se_diff = math.sqrt(\n'
        '        treatment_stats["variance"] / n_c + treatment_stats["variance"] / n_t\n'
        '    )\n'
        '    \n'
        '    # Welch-Satterthwaite degrees of freedom\n'
        '    var_c_n = treatment_stats["variance"] / n_c\n'
        '    var_t_n = treatment_stats["variance"] / n_t',
        '    # Standard error of the difference using each group own variance\n'
        '    se_diff = math.sqrt(\n'
        '        control_stats["variance"] / n_c + treatment_stats["variance"] / n_t\n'
        '    )\n'
        '    \n'
        '    # Welch-Satterthwaite degrees of freedom\n'
        '    var_c_n = control_stats["variance"] / n_c\n'
        '    var_t_n = treatment_stats["variance"] / n_t'
    )
    
    with open(pipeline_path, 'w') as f:
        f.write(code)
    
    print("Applied all fixes to pipeline.py")


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print("Pipeline executed successfully")


if __name__ == "__main__":
    apply_fixes()
    run_pipeline()
