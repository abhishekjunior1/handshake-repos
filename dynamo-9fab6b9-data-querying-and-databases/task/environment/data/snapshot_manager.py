"""
Transaction snapshot management for MVCC isolation.

Builds snapshots that capture which transactions were active (uncommitted)
at a given point in time. The snapshot is used to determine row visibility —
rows created by active (uncommitted) transactions are invisible.
"""


def build_snapshot(txn_id, start_timestamp, commit_log):
    """Build the active transaction set for a snapshot.

    Returns the set of transaction IDs that were active (started but
    not yet committed) at the time this transaction's snapshot was taken.

    A transaction is active if:
    - It started before or at our start_timestamp
    - It has NOT committed before our start_timestamp

    The current transaction (txn_id) should be included in this set
    because its own visibility is handled through the command-ID (cid)
    mechanism, not through the normal snapshot visibility path.

    Args:
        txn_id: Current transaction's ID
        start_timestamp: When the current transaction started
        commit_log: List of {txn_id, start_ts, commit_ts} records

    Returns:
        List of active transaction IDs
    """
    active = []

    for entry in commit_log:
        entry_txn = entry['txn_id']
        entry_start = entry['start_ts']
        entry_commit = entry.get('commit_ts', None)

        # Transaction started before our snapshot time
        if entry_start <= start_timestamp:
            # Not yet committed at our snapshot time
            if entry_commit is None or entry_commit > start_timestamp:
                active.append(entry_txn)

    # Include current transaction in active set
    if txn_id not in active:
        active.append(txn_id)

    return sorted(active)


def is_transaction_committed(txn_id, commit_log, as_of_ts=None):
    """Check if a transaction has committed (optionally before a timestamp).

    Args:
        txn_id: Transaction ID to check
        commit_log: Commit log records
        as_of_ts: If provided, check if committed before this time

    Returns:
        Boolean indicating committed status
    """
    for entry in commit_log:
        if entry['txn_id'] == txn_id:
            commit_ts = entry.get('commit_ts', None)
            if commit_ts is None:
                return False
            if as_of_ts is not None:
                return commit_ts <= as_of_ts
            return True

    # Transaction not in commit log — treat as committed (very old)
    return True
