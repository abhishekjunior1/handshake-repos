"""Tests for CDC ETL pipeline output on hidden configuration 1."""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def actual_output():
    """Load the pipeline's actual output."""
    with open("/app/output.json", "r") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected output for hidden config 1."""
    with open(os.path.join(TESTS_DIR, "expected_output.json"), "r") as f:
        return json.load(f)


class TestWarehouseSnapshot:
    """Tests for the warehouse snapshot section of the output."""

    def test_row_count(self, actual_output, expected_output):
        """Verify the total number of rows in the warehouse snapshot."""
        actual = actual_output["warehouse_snapshot"]["row_count"]
        expected = expected_output["warehouse_snapshot"]["row_count"]
        assert actual == expected, f"Row count: {actual} != {expected}"

    def test_active_count(self, actual_output, expected_output):
        """Verify the count of active (non-deleted) rows."""
        actual = actual_output["warehouse_snapshot"]["active_count"]
        expected = expected_output["warehouse_snapshot"]["active_count"]
        assert actual == expected, f"Active count: {actual} != {expected}"

    def test_deleted_count(self, actual_output, expected_output):
        """Verify the count of soft-deleted rows."""
        actual = actual_output["warehouse_snapshot"]["deleted_count"]
        expected = expected_output["warehouse_snapshot"]["deleted_count"]
        assert actual == expected, f"Deleted count: {actual} != {expected}"

    def test_row_values_preserved_on_partial_update(self, actual_output, expected_output):
        """Verify that NULL columns in UPDATE events preserve prior values.

        When an UPDATE event carries NULL for a column, the existing
        non-NULL value from prior state must be preserved (partial update
        semantics), not overwritten with NULL.
        """
        actual_rows = actual_output["warehouse_snapshot"]["rows"]
        expected_rows = expected_output["warehouse_snapshot"]["rows"]

        for exp_row in expected_rows:
            pk = exp_row.get("_primary_key")
            act_row = next((r for r in actual_rows if r.get("_primary_key") == pk), None)
            assert act_row is not None, f"Missing row for PK {pk}"

            for col, exp_val in exp_row.items():
                if col.startswith("_"):
                    continue
                act_val = act_row.get(col)
                assert act_val == exp_val, (
                    f"Row {pk}, column '{col}': actual={act_val} expected={exp_val}"
                )


class TestSCDHistory:
    """Tests for SCD Type-2 history tracking."""

    def test_total_versions(self, actual_output, expected_output):
        """Verify total number of SCD version records."""
        actual = actual_output["scd_history"]["total_versions"]
        expected = expected_output["scd_history"]["total_versions"]
        assert actual == expected, f"Total versions: {actual} != {expected}"

    def test_entities_with_changes(self, actual_output, expected_output):
        """Verify count of entities that have multiple SCD versions."""
        actual = actual_output["scd_history"]["entities_with_changes"]
        expected = expected_output["scd_history"]["entities_with_changes"]
        assert actual == expected, f"Entities with changes: {actual} != {expected}"

    def test_effective_to_boundaries(self, actual_output, expected_output):
        """Verify that previous SCD versions have correct effective_to timestamps.

        When a new version of an entity is created, the previous version's
        effective_to must be set to the new version's effective_from timestamp,
        creating gap-free temporal boundaries.
        """
        actual_records = actual_output["scd_history"]["records"]
        expected_records = expected_output["scd_history"]["records"]

        for exp_rec in expected_records:
            entity = exp_rec["entity_key"]
            version = exp_rec["version"]
            act_rec = next(
                (r for r in actual_records
                 if r.get("entity_key") == entity and r.get("version") == version),
                None
            )
            assert act_rec is not None, f"Missing SCD record: {entity} v{version}"
            assert act_rec.get("effective_to") == exp_rec.get("effective_to"), (
                f"SCD {entity} v{version}: effective_to "
                f"actual={act_rec.get('effective_to')} expected={exp_rec.get('effective_to')}"
            )


class TestPipelineMetrics:
    """Tests for pipeline processing metrics."""

    def test_dedup_stats(self, actual_output, expected_output):
        """Verify deduplication statistics are correct."""
        actual = actual_output["pipeline_metrics"]["deduplication"]
        expected = expected_output["pipeline_metrics"]["deduplication"]
        assert actual["total_input_events"] == expected["total_input_events"]
        assert actual["deduplicated_count"] == expected["deduplicated_count"]
        assert actual["duplicates_removed"] == expected["duplicates_removed"]

    def test_merge_operations(self, actual_output, expected_output):
        """Verify merge operation counts reflect correct processing order.

        Deduplication before merge should eliminate duplicate events,
        reducing the number of merge conflicts and ensuring accurate
        insert/update/delete counts.
        """
        actual = actual_output["pipeline_metrics"]["merge_operations"]
        expected = expected_output["pipeline_metrics"]["merge_operations"]
        assert actual["inserts"] == expected["inserts"], (
            f"Inserts: {actual['inserts']} != {expected['inserts']}"
        )
        assert actual["updates"] == expected["updates"], (
            f"Updates: {actual['updates']} != {expected['updates']}"
        )
        assert actual["deletes"] == expected["deletes"], (
            f"Deletes: {actual['deletes']} != {expected['deletes']}"
        )
        assert actual["conflicts"] == expected["conflicts"], (
            f"Conflicts: {actual['conflicts']} != {expected['conflicts']}"
        )


class TestFullOutputMatch:
    """Catch-all test for complete output correctness."""

    def test_full_output_match(self, actual_output, expected_output):
        """Verify complete output matches expected output exactly.

        This catch-all ensures no field is missed by individual tests.
        All sections must match: warehouse_snapshot, scd_history, and
        pipeline_metrics.
        """
        assert actual_output == expected_output, (
            "Full output does not match expected output"
        )
