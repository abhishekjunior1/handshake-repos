"""Solve script that patches the 3 bugs in the K8s pod scheduling simulator and runs the pipeline."""

import subprocess
import sys


def patch_file(filepath, old_str, new_str):
    """Read a file, replace old_str with new_str, and write it back."""
    with open(filepath, "r") as f:
        content = f.read()

    if old_str not in content:
        print(f"ERROR: Could not find target string in {filepath}")
        print(f"  Looking for: {repr(old_str[:80])}")
        sys.exit(1)

    content = content.replace(old_str, new_str, 1)

    with open(filepath, "w") as f:
        f.write(content)

    print(f"Patched {filepath}")


def main():
    # Bug 1 (pipeline.py): get_node_max_pods reads cluster-level default_max_pods
    # instead of the per-node allocatable.pods value. The cluster-wide default (110)
    # doesn't reflect individual node capacity limits.
    # Fix: read from node's own status.allocatable.pods field.
    patch_file(
        "/app/pipeline.py",
        '    cluster_default = cluster_config.get("cluster", {}).get("default_max_pods", 110)\n'
        '    return cluster_default',
        '    node_max = node.get("status", {}).get("allocatable", {}).get("pods", 110)\n'
        '    return node_max',
    )

    # Bug 2 (resource_calculator.py): Fits against limits instead of requests.
    # The K8s scheduler always schedules based on resource requests, not limits.
    # Fix: use requests for both CPU and memory fit computation.
    patch_file(
        "/app/resource_calculator.py",
        '        # Fit computation against resource limits for capacity reservation\n'
        '        total_cpu_needed += limits.get("cpu_millicores", requests.get("cpu_millicores", 0))\n'
        '        total_memory_needed += limits.get("memory_mb", requests.get("memory_mb", 0))',
        '        # Fit computation against resource requests for scheduling\n'
        '        total_cpu_needed += requests.get("cpu_millicores", 0)\n'
        '        total_memory_needed += requests.get("memory_mb", 0)',
    )

    # Bug 3 (affinity_evaluator.py): Anti-affinity penalty is multiplied by
    # matching_colocated count, making penalty proportional to density.
    # K8s preferred anti-affinity uses weight as a flat penalty (boolean trigger),
    # not scaled by how many matching pods exist.
    # Fix: subtract just the weight when any matching pods are colocated.
    patch_file(
        "/app/affinity_evaluator.py",
        "            # Scale penalty by colocation density for proportional repulsion\n"
        "            anti_affinity_score -= weight * matching_colocated",
        "            # Apply flat anti-affinity penalty when colocated pods match\n"
        "            anti_affinity_score -= weight",
    )

    # Run the pipeline
    print("Running pipeline...")
    result = subprocess.run(
        [sys.executable, "pipeline.py"],
        cwd="/app",
        capture_output=True,
        text=True,
    )

    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)

    if result.returncode != 0:
        print(f"Pipeline failed with return code {result.returncode}")
        sys.exit(result.returncode)

    print("Pipeline completed successfully. Output written to /app/output.json")


if __name__ == "__main__":
    main()
