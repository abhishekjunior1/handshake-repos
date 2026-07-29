"""
Solution: patches the two bugs in pipeline.py and runs the pipeline.

Bug 1: OSPF cost computation uses interface bandwidth instead of link bandwidth.
Fix: Replace iface["bandwidth"] with link["bandwidth"] in _compute_all_ospf_costs.

Bug 2: ACL interface_scope resolution uses the destination subnet (potentially /24)
instead of the flow's actual destination IP as a /32 host route.
Fix: Replace dest_subnet["network"] with flows[0]["destination_ip"] and
dest_subnet["prefix_length"] with 32.
"""

import subprocess
import sys


def patch_pipeline():
    """Apply bug fixes to pipeline.py via string replacement."""
    with open("/app/pipeline.py", "r") as f:
        code = f.read()

    # Fix Bug 1: Use link bandwidth instead of interface bandwidth for OSPF cost
    code = code.replace(
        'iface_bw = iface["bandwidth"]',
        'iface_bw = link["bandwidth"]',
    )

    # Fix Bug 2: Use flow's destination IP as /32 host route instead of
    # resolving the interface subnet (which could be /24 or broader)
    code = code.replace(
        'scope_network = dest_subnet["network"]',
        'scope_network = flows[0]["destination_ip"]',
    )
    code = code.replace(
        'scope_prefix = dest_subnet["prefix_length"]',
        "scope_prefix = 32",
    )

    with open("/app/pipeline.py", "w") as f:
        f.write(code)


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        ["python3", "/app/pipeline.py", "/app/config.json", "/app/output.json"],
        cwd="/app",
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"Pipeline failed: {result.stderr}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    patch_pipeline()
    run_pipeline()
