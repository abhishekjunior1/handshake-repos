"""Tests for CDC ETL pipeline output on hidden configuration 2."""

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
    """Load the expected output for hidden config 2."""
    with open(os.path.join(TESTS_DIR, "expected_output_2.json"), "r") as f:
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

    def test_partial_update_preserves_values(self, actual_output, expected_output):
        """Verify that UPDATE events with NULL columns preserve existing values.

        Partial update semantics require that only non-NULL columns from the
        UPDATE event overwrite the destination row. NULL columns must not
        replace existing non-NULL values.
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

    def test_effective_to_temporal_boundaries(self, actual_output, expected_output):
        """Verify SCD version boundaries are correctly closed.

        Each superseded version must have its effective_to set to the
        timestamp of the succeeding version's effective_from, ensuring
        gap-free temporal coverage of the entity's history.
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

    def test_dedup_statistics(self, actual_output, expected_output):
        """Verify deduplication metrics reflect correct duplicate detection."""
        actual = actual_output["pipeline_metrics"]["deduplication"]
        expected = expected_output["pipeline_metrics"]["deduplication"]
        assert actual["total_input_events"] == expected["total_input_events"]
        assert actual["deduplicated_count"] == expected["deduplicated_count"]
        assert actual["duplicates_removed"] == expected["duplicates_removed"]

    def test_merge_operation_counts(self, actual_output, expected_output):
        """Verify merge statistics reflect dedup-before-merge ordering.

        When deduplication occurs before merge, duplicate events are
        eliminated before they can create spurious merge conflicts.
        """
        actual = actual_output["pipeline_metrics"]["merge_operations"]
        expected = expected_output["pipeline_metrics"]["merge_operations"]
        assert actual["inserts"] == expected["inserts"], (
            f"Inserts: {actual['inserts']} != {expected['inserts']}"
        )
        assert actual["updates"] == expected["updates"], (
            f"Updates: {actual['updates']} != {expected['updates']}"
        )
        assert actual["deletes"] == expected["deletes"]
        assert actual["conflicts"] == expected["conflicts"], (
            f"Conflicts: {actual['conflicts']} != {expected['conflicts']}"
        )


class TestFullOutputMatch:
    """Catch-all test for complete output correctness."""

    def test_full_output_match(self, actual_output, expected_output):
        """Verify complete output matches expected output exactly.

        This catch-all ensures no field is missed by individual targeted
        tests. All sections must match: warehouse_snapshot, scd_history,
        and pipeline_metrics.
        """
        assert actual_output == expected_output, (
            "Full output does not match expected output"
        )
