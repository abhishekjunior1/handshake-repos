"""
Solve script for the EVA pipeline.
Patches three bugs across three files:
1. pipeline.py: GPD fitted to raw exceedances instead of cluster maxima
2. declustering.py: Uses first-of-cluster instead of max-of-cluster
3. return_level.py: Missing extremal index correction in exceedance probability
"""

PIPELINE_PATH = "/app/pipeline.py"
DECLUSTERING_PATH = "/app/declustering.py"
RETURN_LEVEL_PATH = "/app/return_level.py"


def patch_file(filepath, old_str, new_str):
    """Replace exact string in file."""
    with open(filepath, "r") as f:
        content = f.read()
    if old_str not in content:
        raise ValueError(f"Patch target not found in {filepath}:\n{repr(old_str[:80])}")
    content = content.replace(old_str, new_str, 1)
    with open(filepath, "w") as f:
        f.write(content)


def fix_bug1():
    """Fix: GPD should be fitted to cluster maxima, not raw exceedances."""
    patch_file(
        PIPELINE_PATH,
        "gpd_params = estimate_gpd_parameters(exceedances)",
        "gpd_params = estimate_gpd_parameters(cluster_maxima)"
    )


def fix_bug2():
    """Fix: Cluster maxima should be the actual maximum of each cluster."""
    patch_file(
        DECLUSTERING_PATH,
        "cluster_max_val = observations[cluster[-1]] - threshold",
        "cluster_max_val = max(observations[idx] for idx in cluster) - threshold"
    )


def fix_bug3():
    """Fix: Exceedance probability must account for extremal index."""
    patch_file(
        RETURN_LEVEL_PATH,
        "prob = p_exceed / exceedance_rate if exceedance_rate > 0 else 1.0",
        "prob = p_exceed / (exceedance_rate * extremal_index) if exceedance_rate > 0 else 1.0"
    )


if __name__ == "__main__":
    print("Applying fixes...")
    fix_bug1()
    print("  Fixed: GPD fitted to cluster maxima")
    fix_bug2()
    print("  Fixed: Cluster maxima uses actual maximum")
    fix_bug3()
    print("  Fixed: Return level uses extremal index correction")
    print("Done.")
