"""
Solution: Fix two MVCC snapshot visibility bugs in the pipeline.

Bug 1: The snapshot includes the current transaction in its own active
set. This causes self-created row versions to be evaluated through the
wrong code path and can prevent proper deletion visibility for the
current transaction's overwrites. Fix: exclude self from active set.

Bug 2: Self-visibility check uses strict greater-than (v_cid > current_cid)
which incorrectly makes versions at the current command ID visible.
A version created at the current cid represents the statement's own
output-in-progress and should NOT be visible. Fix: use >= comparison.
"""

import subprocess


def fix_pipeline():
    """Apply fixes to pipeline.py."""
    with open('/app/pipeline.py', 'r') as f:
        content = f.read()

    # Fix Bug 1: Exclude self from active transaction set
    content = content.replace(
        '    # Include the current transaction in the active set — this prevents\n'
        '    # the snapshot from seeing its own uncommitted modifications through\n'
        '    # the normal visibility path. Self-visibility is handled separately\n'
        '    # via the command-ID (cid) mechanism for intra-transaction ordering.\n'
        '    active_txns = build_snapshot(txn_id, txn_start_ts, commit_log)',
        '    # Build active set and exclude self — self-visibility is handled\n'
        '    # via the command-ID (cid) mechanism, not the snapshot active set.\n'
        '    active_txns = [t for t in build_snapshot(txn_id, txn_start_ts, commit_log)\n'
        '                   if t != txn_id]'
    )

    # Fix Bug 2: Use >= for cid comparison (exclude current cid)
    content = content.replace(
        '                # Use strict greater-than for command ordering — a version\n'
        '                # created at the current command ID represents a concurrent\n'
        '                # modification within the same statement and should be\n'
        '                # visible for read-after-write consistency within statements.\n'
        '                if v_cid > current_cid:',
        '                # Exclude versions at or above current cid — a version at\n'
        '                # exactly the current cid is being created NOW and should\n'
        '                # not be visible to the creating statement itself.\n'
        '                if v_cid >= current_cid:'
    )

    with open('/app/pipeline.py', 'w') as f:
        f.write(content)

    print("Applied 2 fixes to pipeline.py")


def run_pipeline():
    """Run the fixed pipeline."""
    result = subprocess.run(
        ['python3', '/app/pipeline.py'],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(f"STDERR: {result.stderr}")
    return result.returncode


if __name__ == '__main__':
    fix_pipeline()
    exit_code = run_pipeline()
    exit(exit_code)
