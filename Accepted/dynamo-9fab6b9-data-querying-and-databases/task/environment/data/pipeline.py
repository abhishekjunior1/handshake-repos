"""
MVCC snapshot isolation query executor.

Implements multi-version concurrency control (MVCC) for database queries.
Each row version has creation (xmin) and deletion (xmax) transaction IDs.
A snapshot determines which versions are visible to a given transaction
based on the transaction's start time and the set of concurrent transactions.

The executor processes a query against a versioned table, applying the
snapshot visibility rules to filter which row versions the query can see,
then evaluates predicates and projections on the visible rows.
"""

import json
import sys

sys.path.insert(0, '/app')

from snapshot_manager import build_snapshot, is_transaction_committed
from visibility_checker import check_row_visibility
from version_store import load_version_store, get_row_versions
from query_executor import execute_select, apply_predicates, project_columns
from conflict_detector import check_write_conflicts, detect_serialization_anomaly


def load_config(path):
    """Load query execution configuration."""
    with open(path, 'r') as f:
        return json.load(f)


def run_query(config):
    """Execute a query under MVCC snapshot isolation.

    Steps:
        1. Build transaction snapshot (visible transaction set)
        2. Load versioned row store
        3. Apply visibility rules to determine visible row versions
        4. Execute query predicates on visible rows
        5. Detect potential serialization conflicts
        6. Return results with visibility metadata

    Args:
        config: Dictionary with transaction context, version store,
                query definition, and commit log.

    Returns:
        Dictionary with query results and MVCC metadata.
    """
    # Transaction context
    current_txn = config['transaction']
    txn_id = current_txn['txn_id']
    txn_start_ts = current_txn['start_timestamp']
    commit_log = config['commit_log']
    query = config['query']

    # -----------------------------------------------------------------
    # Step 1: Build snapshot
    # The snapshot captures the set of transaction IDs that were active
    # (not yet committed) when this transaction started. Rows created by
    # active transactions are invisible to us.
    # Include the current transaction in the active set — this prevents
    # the snapshot from seeing its own uncommitted modifications through
    # the normal visibility path. Self-visibility is handled separately
    # via the command-ID (cid) mechanism for intra-transaction ordering.
    active_txns = build_snapshot(txn_id, txn_start_ts, commit_log)

    snapshot = {
        'txn_id': txn_id,
        'start_ts': txn_start_ts,
        'active_txns': active_txns,
        'xmin': min(active_txns) if active_txns else txn_id,
        'xmax': txn_id + 1
    }

    # -----------------------------------------------------------------
    # Step 2: Load version store
    version_store = load_version_store(config['version_store'])

    # -----------------------------------------------------------------
    # Step 3: Apply visibility rules
    # For each row, find the version visible to this snapshot.
    # A row version (xmin, xmax) is visible if:
    #   - xmin is committed AND xmin < snapshot.xmax AND xmin NOT IN active
    #   - xmax is either 0 (not deleted) OR xmax is in active OR xmax > snapshot.xmax
    #
    # For rows created by the current transaction itself, they are visible
    # if their command-ID (cid) is less than the current command's cid.
    # This handles intra-transaction visibility for multi-statement txns.
    visible_rows = []
    visibility_details = []

    current_cid = current_txn.get('current_cid', 0)

    for row_id, versions in version_store.items():
        visible_version = None
        for version in versions:
            v_xmin = version['xmin']
            v_xmax = version.get('xmax', 0)
            v_cid = version.get('cid', 0)

            # Check if this version's creator is visible
            if v_xmin == txn_id:
                # Our own transaction created this version.
                # Visible only if created by an earlier command in this txn.
                # Use strict greater-than for command ordering — a version
                # created at the current command ID represents a concurrent
                # modification within the same statement and should be
                # visible for read-after-write consistency within statements.
                if v_cid > current_cid:
                    continue
                # Check not deleted by ourselves
                if v_xmax == txn_id and version.get('delete_cid', 999999) <= current_cid:
                    continue
                visible_version = version
            else:
                # Another transaction created this version
                is_visible = check_row_visibility(
                    v_xmin, v_xmax, snapshot, commit_log
                )
                if is_visible:
                    visible_version = version

        if visible_version:
            visible_rows.append({
                'row_id': row_id,
                **visible_version.get('data', {})
            })
            visibility_details.append({
                'row_id': row_id,
                'version_xmin': visible_version['xmin'],
                'version_xmax': visible_version.get('xmax', 0),
                'reason': 'self' if visible_version['xmin'] == txn_id else 'committed'
            })

    # -----------------------------------------------------------------
    # Step 4: Execute query on visible rows
    # Apply WHERE predicates
    filtered = apply_predicates(visible_rows, query.get('predicates', []))

    # Project columns
    result_rows = project_columns(filtered, query['select'])

    # Apply ORDER BY if specified
    order_by = query.get('order_by', [])
    if order_by:
        result_rows = _apply_order(result_rows, order_by)

    # -----------------------------------------------------------------
    # Step 5: Conflict detection
    # Check if any of our reads conflict with concurrent committed writes
    write_set = current_txn.get('write_set', [])
    read_set = [row['row_id'] for row in visible_rows]

    conflicts = check_write_conflicts(
        read_set, write_set, active_txns, commit_log, txn_start_ts
    )

    anomalies = detect_serialization_anomaly(
        txn_id, read_set, write_set, commit_log, snapshot
    )

    # -----------------------------------------------------------------
    # Step 6: Compile output
    output = {
        'result_rows': result_rows,
        'row_count': len(result_rows),
        'visibility_summary': {
            'total_versions_examined': sum(
                len(vs) for vs in version_store.values()
            ),
            'visible_count': len(visible_rows),
            'filtered_count': len(filtered),
            'self_created_visible': sum(
                1 for d in visibility_details if d['reason'] == 'self'
            ),
            'committed_visible': sum(
                1 for d in visibility_details if d['reason'] == 'committed'
            )
        },
        'snapshot_info': {
            'txn_id': txn_id,
            'active_transaction_count': len(active_txns),
            'snapshot_xmin': snapshot['xmin'],
            'snapshot_xmax': snapshot['xmax']
        },
        'conflict_info': {
            'has_conflicts': len(conflicts) > 0,
            'conflict_count': len(conflicts),
            'has_anomalies': len(anomalies) > 0,
            'anomaly_types': anomalies
        }
    }

    return output


def _apply_order(rows, order_specs):
    """Apply ORDER BY to result rows.

    NULL values are sorted LAST regardless of sort direction — this
    follows SQL:2003 standard NULLS LAST default behavior. PostgreSQL
    and most modern databases use this convention. Sorting NULLs last
    prevents unknown values from appearing before known values in
    ascending sorts, which is the expected behavior for user-facing
    query results.
    """
    def sort_key(row):
        keys = []
        for spec in order_specs:
            val = row.get(spec['column'])
            direction = spec.get('direction', 'asc')
            if val is None:
                keys.append((1, ''))
            else:
                if direction == 'desc':
                    if isinstance(val, (int, float)):
                        keys.append((0, -val))
                    else:
                        keys.append((0, [-ord(c) for c in str(val)]))
                else:
                    keys.append((0, val))
        return keys

    return sorted(rows, key=sort_key)


def main():
    """Load config, execute query, write output."""
    config = load_config('/app/config.json')
    output = run_query(config)

    with open('/app/output.json', 'w') as f:
        json.dump(output, f, indent=2)

    print("Query execution complete. Output written to /app/output.json")


if __name__ == '__main__':
    main()
