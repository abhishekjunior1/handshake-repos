"""
Solution script for the service mesh traffic routing pipeline.

Patches three integration bugs in pipeline.py and reruns the pipeline
to produce correct routing output.
"""

import subprocess
import sys


def apply_patches():
    """Apply all three bug fixes to /app/pipeline.py using string replacement."""
    with open("/app/pipeline.py", "r") as f:
        content = f.read()

    # Patch 1: Fix circuit breaker ordering
    # Move CB evaluation before retry budget consumption
    content = content.replace(
        """        # Consume retry budget first, then assess circuit state
        if attempts > 1:
            retry_result = handler.execute_retry(current_time)
            if not retry_result["allowed"]:
                final_status = "retries_exhausted"
                break

        # Evaluate circuit breaker for selected backend
        cb_allowed = cb_registry.allow_request(
            target.backend_id, current_time)

        if cb_allowed:
            routed_to = target.backend_id
            final_status = "routed"
            break
        else:
            # Backend circuit is open, try next in ring
            remaining = [b for b in healthy_backends
                         if b.backend_id != target.backend_id]
            if remaining:
                ring_alt = ConsistentHashRing(ring_size=65536, virtual_nodes=150)
                ring_alt.build_ring(remaining)
                selected_backend = ring_alt.get_node(hash_key)
            else:
                final_status = "all_circuits_open"
                break""",
        """        # Evaluate circuit breaker before consuming retry budget
        cb_allowed = cb_registry.allow_request(
            target.backend_id, current_time)

        if not cb_allowed:
            # Backend circuit is open, try next without consuming retries
            remaining = [b for b in healthy_backends
                         if b.backend_id != target.backend_id]
            if remaining:
                ring_alt = ConsistentHashRing(ring_size=65536, virtual_nodes=150)
                ring_alt.build_ring(remaining)
                selected_backend = ring_alt.get_node(hash_key)
                continue
            else:
                final_status = "all_circuits_open"
                break

        if attempts > 1:
            retry_result = handler.execute_retry(current_time)
            if not retry_result["allowed"]:
                final_status = "retries_exhausted"
                break

        routed_to = target.backend_id
        final_status = "routed"
        break"""
    )

    # Patch 2: Fix hash key to use source+destination for per-pair backend affinity
    content = content.replace(
        "    # Hash only the source service for connection pool affinity\n"
        "    return source",
        "    # Hash source+destination for per-pair backend affinity\n"
        '    return f"{source}:{destination}"'
    )

    # Patch 3: Fix health check to use last_heartbeat_timestamp
    content = content.replace(
        "    # Use registration timestamp as the TTL anchor point\n"
        "    return backend.registration_timestamp + ttl > current_time",
        "    # Use last heartbeat timestamp as the TTL anchor point\n"
        "    return backend.last_heartbeat_timestamp + ttl > current_time"
    )

    with open("/app/pipeline.py", "w") as f:
        f.write(content)

    print("All patches applied successfully.")


def run_pipeline():
    """Execute the patched pipeline."""
    result = subprocess.run(
        [sys.executable, "/app/pipeline.py"],
        cwd="/app",
        capture_output=True,
        text=True
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        sys.exit(result.returncode)


if __name__ == "__main__":
    apply_patches()
    run_pipeline()
