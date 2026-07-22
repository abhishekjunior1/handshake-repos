An MVCC snapshot isolation query executor at `/app/pipeline.py` processes SQL queries against a versioned row store using multi-version concurrency control. It uses modules `/app/snapshot_manager.py`, `/app/visibility_checker.py`, `/app/version_store.py`, `/app/query_executor.py`, and `/app/conflict_detector.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` and writes `/app/output.json`.

The executor produces correct results on the current transaction configuration but has bugs that cause incorrect row visibility on transactions with different concurrency characteristics. Find and fix the bugs so the executor handles all valid transaction scenarios correctly, including multi-statement transactions with self-visibility semantics and concurrent transaction interference.

Do not rewrite from scratch — preserve the existing module structure, the NULLS LAST ordering convention, and the xmax exclusive upper bound semantics (snapshot xmax = txn_id + 1). The fixed executor will be tested on a different transaction configuration than the one at `/app/config.json`.

Output: `/app/output.json` — a JSON object with: `result_rows` (list of row dicts), `row_count` (integer), `visibility_summary` (dict with total_versions_examined, visible_count, filtered_count, self_created_visible, committed_visible), `snapshot_info` (dict with txn_id, active_transaction_count, snapshot_xmin, snapshot_xmax), and `conflict_info` (dict with has_conflicts, conflict_count, has_anomalies, anomaly_types).
