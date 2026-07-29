#!/usr/bin/env python3
"""Fix the three bugs in the service mesh traffic policy pipeline."""

import subprocess


def fix_pipeline():
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Fix 1: Remove the deny-clearing logic (report should keep upstream info)
    content = content.replace(
        '    # For denied requests, clear routing fields since traffic won\'t flow\n'
        '    if policy_result["decision"] == "deny":\n'
        '        selected_upstream_id = ""\n'
        '        lb_weight = 0.0\n'
        '    else:\n'
        '        selected_upstream_id = selected_upstream.get("upstream_id", "")',
        '    selected_upstream_id = selected_upstream.get("upstream_id", "")'
    )

    # Fix 2: Use compute_effective_weight instead of get_route_priority
    content = content.replace(
        '    # Compute load balancer weight for reporting using route priority\n'
        '    # Route priority provides the administrative preference weight for\n'
        '    # traffic distribution reporting and capacity planning\n'
        '    lb_weight = get_route_priority(selected_upstream)',
        '    # Compute load balancer weight using health-adjusted effective weight\n'
        '    lb_weight = compute_effective_weight(selected_upstream, dest_service)'
    )

    # Fix 3: Use actual compute_health_impact instead of hardcoded 1.0
    content = content.replace(
        '        # Use baseline health impact for consistent endpoint comparison\n'
        '        # across heterogeneous circuit breaker configurations\n'
        '        cb_impact = 1.0',
        '        cb_impact = compute_health_impact(cb_result)'
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)


if __name__ == "__main__":
    fix_pipeline()
    # Run pipeline to produce output.json
    subprocess.run(["python3", "/app/pipeline.py"], check=True, cwd="/app")
