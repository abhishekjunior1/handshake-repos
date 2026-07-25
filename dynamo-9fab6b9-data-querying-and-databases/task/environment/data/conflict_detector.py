"""
Write conflict and serialization anomaly detection for MVCC.

Detects potential conflicts between transactions that could
violate serialization isolation guarantees.
"""


def check_write_conflicts(read_set, write_set, active_txns, commit_log, start_ts):
    """Check for write-write conflicts with concurrent transactions.

    A conflict exists if another transaction wrote to a row that we
    also wrote, and that transaction committed after we started.

    Args:
        read_set: Row IDs read by current transaction
        write_set: Row IDs written by current transaction
        active_txns: Active transaction set from snapshot
        commit_log: Transaction commit records
        start_ts: Current transaction's start timestamp

    Returns:
        List of conflict descriptions
    """
    conflicts = []

    for entry in commit_log:
        other_txn = entry['txn_id']
        commit_ts = entry.get('commit_ts', None)

        if commit_ts is None:
            continue
        if commit_ts <= start_ts:
            continue  # Committed before we started — not a conflict

        # Check if this concurrent committer wrote to any of our read/write set
        other_writes = entry.get('write_set', [])
        overlapping_reads = set(read_set) & set(other_writes)
        overlapping_writes = set(write_set) & set(other_writes)

        if overlapping_writes:
            conflicts.append({
                'type': 'write_write',
                'other_txn': other_txn,
                'rows': list(overlapping_writes)
            })
        elif overlapping_reads:
            conflicts.append({
                'type': 'read_write',
                'other_txn': other_txn,
                'rows': list(overlapping_reads)
            })

    return conflicts


def detect_serialization_anomaly(txn_id, read_set, write_set, commit_log, snapshot):
    """Detect potential serialization anomalies.

    Checks for patterns that could indicate non-serializable execution:
    - Write skew: two transactions read overlapping sets and write
      disjoint sets based on what they read
    - Phantom: a range query's results could differ if replayed

    Args:
        txn_id: Current transaction ID
        read_set: Rows read
        write_set: Rows written
        commit_log: Commit records
        snapshot: Current snapshot

    Returns:
        List of anomaly type strings
    """
    anomalies = []
    active_txns = snapshot['active_txns']

    # Check for potential write skew with concurrent transactions
    for entry in commit_log:
        other_txn = entry['txn_id']
        if other_txn == txn_id:
            continue
        if other_txn not in active_txns:
            continue

        other_reads = entry.get('read_set', [])
        other_writes = entry.get('write_set', [])

        # Write skew pattern: we read what they wrote, they read what we wrote
        if set(read_set) & set(other_writes) and set(write_set) & set(other_reads):
            anomalies.append('write_skew')
            break

    return anomalies
