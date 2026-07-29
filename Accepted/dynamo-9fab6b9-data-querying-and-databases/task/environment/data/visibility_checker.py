"""
Row version visibility checking for MVCC.

Determines whether a specific row version is visible to a transaction
based on the version's xmin/xmax and the transaction's snapshot.

Visibility rules (for rows NOT created by the current transaction):
- The creating transaction (xmin) must be committed
- The creating transaction must NOT be in the snapshot's active set
- The row must NOT be deleted (xmax = 0) OR the deleting transaction
  must be uncommitted (in active set or > snapshot.xmax)
"""

from snapshot_manager import is_transaction_committed


def check_row_visibility(xmin, xmax, snapshot, commit_log):
    """Check if a row version is visible to the given snapshot.

    A version is visible if its creator committed before our snapshot
    AND the version hasn't been deleted by a visible transaction.

    Args:
        xmin: Transaction ID that created this version
        xmax: Transaction ID that deleted this version (0 = not deleted)
        snapshot: Snapshot dictionary with txn_id, active_txns, xmin, xmax
        commit_log: Transaction commit records

    Returns:
        Boolean indicating visibility
    """
    active_txns = snapshot['active_txns']
    snap_xmax = snapshot['xmax']

    # Rule 1: Creator must be committed
    if not is_transaction_committed(xmin, commit_log, as_of_ts=snapshot['start_ts']):
        return False

    # Rule 2: Creator must not be in our active set
    if xmin in active_txns:
        return False

    # Rule 3: Creator must be less than snapshot xmax
    if xmin >= snap_xmax:
        return False

    # Rule 4: Check deletion visibility
    if xmax != 0:
        # Row has been deleted — check if the deletion is visible to us
        # If deleter committed and is not in active set, row is gone
        if is_transaction_committed(xmax, commit_log, as_of_ts=snapshot['start_ts']):
            if xmax not in active_txns and xmax < snap_xmax:
                return False  # Deletion is visible — row is gone

    # Version is visible
    return True


def check_self_visibility(version, txn_id, current_cid):
    """Check visibility of a version created by the current transaction.

    For intra-transaction visibility, a row is visible if it was
    created by a prior command (lower cid) and not yet deleted.

    Args:
        version: Row version dict with xmin, cid, xmax, delete_cid
        txn_id: Current transaction ID
        current_cid: Current command ID within the transaction

    Returns:
        Boolean indicating visibility
    """
    if version['xmin'] != txn_id:
        return False

    v_cid = version.get('cid', 0)

    # Must be created by a prior command (strictly less than current)
    if v_cid >= current_cid:
        return False

    # Check if deleted by ourselves before current command
    v_xmax = version.get('xmax', 0)
    if v_xmax == txn_id:
        delete_cid = version.get('delete_cid', 999999)
        if delete_cid < current_cid:
            return False

    return True
