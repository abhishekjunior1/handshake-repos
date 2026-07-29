"""Tests for the MVCC snapshot isolation query executor.

Validates that the executor correctly applies snapshot visibility rules,
handles self-created row versions with proper command-ID semantics,
excludes uncommitted concurrent transactions, and reports accurate
visibility metadata.
"""

import json

EXPECTED_PATH = '/tests/expected_output.json'
OUTPUT_PATH = '/app/output.json'


def load_outputs():
    """Load expected and actual output files."""
    with open(EXPECTED_PATH, 'r') as f:
        expected = json.load(f)
    with open(OUTPUT_PATH, 'r') as f:
        actual = json.load(f)
    return expected, actual


class TestResultRows:
    """Tests for query result correctness under MVCC visibility."""

    def test_row_count(self):
        """Verify correct number of visible rows after predicate filtering."""
        expected, actual = load_outputs()
        assert actual['row_count'] == expected['row_count'], \
            f"Row count: expected {expected['row_count']}, got {actual['row_count']}"

    def test_result_values(self):
        """Verify each result row has correct values from visible versions."""
        expected, actual = load_outputs()
        for i, (exp_row, act_row) in enumerate(zip(expected['result_rows'], actual['result_rows'])):
            for key in exp_row:
                assert act_row.get(key) == exp_row[key], \
                    f"Row {i} '{key}': expected {exp_row[key]}, got {act_row.get(key)}"

    def test_result_order(self):
        """Verify results are correctly ordered."""
        expected, actual = load_outputs()
        exp_ids = [r.get('id') for r in expected['result_rows']]
        act_ids = [r.get('id') for r in actual['result_rows']]
        assert act_ids == exp_ids, \
            f"Row ordering: expected {exp_ids}, got {act_ids}"


class TestVisibility:
    """Tests for MVCC visibility rule application."""

    def test_visible_count(self):
        """Verify total visible row count before predicate filtering."""
        expected, actual = load_outputs()
        assert actual['visibility_summary']['visible_count'] == \
               expected['visibility_summary']['visible_count'], \
            f"Visible count: expected {expected['visibility_summary']['visible_count']}, got {actual['visibility_summary']['visible_count']}"

    def test_self_created_visible(self):
        """Verify correct self-created version visibility via cid semantics."""
        expected, actual = load_outputs()
        assert actual['visibility_summary']['self_created_visible'] == \
               expected['visibility_summary']['self_created_visible'], \
            f"Self-created visible: expected {expected['visibility_summary']['self_created_visible']}, got {actual['visibility_summary']['self_created_visible']}"

    def test_committed_visible(self):
        """Verify correct committed version visibility via snapshot rules."""
        expected, actual = load_outputs()
        assert actual['visibility_summary']['committed_visible'] == \
               expected['visibility_summary']['committed_visible'], \
            f"Committed visible: expected {expected['visibility_summary']['committed_visible']}, got {actual['visibility_summary']['committed_visible']}"

    def test_filtered_count(self):
        """Verify predicate filtering is applied after visibility check."""
        expected, actual = load_outputs()
        assert actual['visibility_summary']['filtered_count'] == \
               expected['visibility_summary']['filtered_count']


class TestSnapshot:
    """Tests for snapshot construction correctness."""

    def test_active_count(self):
        """Verify active transaction count excludes self."""
        expected, actual = load_outputs()
        assert actual['snapshot_info']['active_transaction_count'] == \
               expected['snapshot_info']['active_transaction_count'], \
            f"Active count: expected {expected['snapshot_info']['active_transaction_count']}, got {actual['snapshot_info']['active_transaction_count']}"

    def test_snapshot_xmin(self):
        """Verify snapshot xmin is the lowest active transaction ID."""
        expected, actual = load_outputs()
        assert actual['snapshot_info']['snapshot_xmin'] == \
               expected['snapshot_info']['snapshot_xmin'], \
            f"Snapshot xmin: expected {expected['snapshot_info']['snapshot_xmin']}, got {actual['snapshot_info']['snapshot_xmin']}"

    def test_snapshot_xmax(self):
        """Verify snapshot xmax is one past the current transaction ID."""
        expected, actual = load_outputs()
        assert actual['snapshot_info']['snapshot_xmax'] == \
               expected['snapshot_info']['snapshot_xmax']


class TestConflicts:
    """Tests for conflict detection."""

    def test_conflict_detection(self):
        """Verify conflict detection results match expected."""
        expected, actual = load_outputs()
        assert actual['conflict_info']['has_conflicts'] == \
               expected['conflict_info']['has_conflicts']
        assert actual['conflict_info']['conflict_count'] == \
               expected['conflict_info']['conflict_count']

    def test_anomaly_detection(self):
        """Verify serialization anomaly detection."""
        expected, actual = load_outputs()
        assert actual['conflict_info']['has_anomalies'] == \
               expected['conflict_info']['has_anomalies']
