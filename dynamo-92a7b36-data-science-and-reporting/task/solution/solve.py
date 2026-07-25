"""
Oracle solution: patches all bugs in the meta-analysis pipeline and runs it.
"""

import subprocess
import sys


def patch_random_effects():
    """Fix Bug 1: prediction interval uses k-1 df instead of k-2."""
    filepath = "/app/random_effects.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy code uses df = k - 1 for the prediction interval
    # Fix: use df = k - 2 (accounts for estimation of both mu and tau²)
    content = content.replace(
        "    df = k - 1",
        "    df = k - 2",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_report_generator():
    """Fix Bug 2: subgroup analysis uses overall tau² instead of per-subgroup tau²."""
    filepath = "/app/report_generator.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy code uses overall_tau_squared for subgroup RE weights
    # Fix: compute per-subgroup tau² and use that instead
    content = content.replace(
        "        # Use overall tau² for subgroup weights (common heterogeneity assumption)\n"
        "        re_weights = compute_random_effects_weights(sg_ses, overall_tau_squared)",
        "        # Compute per-subgroup heterogeneity and use subgroup-specific tau²\n"
        "        sg_het = estimate_heterogeneity(sg_effects, sg_ses)\n"
        "        sg_tau_sq = sg_het[\"tau_squared\"]\n"
        "        re_weights = compute_random_effects_weights(sg_ses, sg_tau_sq)",
    )

    # Update the prediction interval to use sg_tau_sq
    content = content.replace(
        "        pi_lower, pi_upper = compute_prediction_interval(\n"
        "            pooled, se_pooled, overall_tau_squared, k\n"
        "        )",
        "        pi_lower, pi_upper = compute_prediction_interval(\n"
        "            pooled, se_pooled, sg_tau_sq, k\n"
        "        )",
    )

    # Remove the duplicate sg_het computation that comes after
    content = content.replace(
        "        # Subgroup heterogeneity\n"
        "        sg_het = estimate_heterogeneity(sg_effects, sg_ses)",
        "        # Subgroup heterogeneity (already computed above)",
    )

    with open(filepath, "w") as f:
        f.write(content)


def patch_egger_test():
    """Fix Bug 3: Egger weights use normalized precision instead of inverse-variance."""
    filepath = "/app/egger_test.py"
    with open(filepath, "r") as f:
        content = f.read()

    # The buggy _compute_egger_weights normalizes by total precision
    # Fix: use standard inverse-variance weights (1/SE²)
    content = content.replace(
        "    total_precision = sum(1.0 / se for se in std_errors)\n"
        "    weights = [(1.0 / se) / total_precision for se in std_errors]",
        "    weights = [1.0 / (se * se) for se in std_errors]",
    )

    with open(filepath, "w") as f:
        f.write(content)


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)
    print(result.stdout)


if __name__ == "__main__":
    patch_random_effects()
    patch_report_generator()
    patch_egger_test()
    run_pipeline()
