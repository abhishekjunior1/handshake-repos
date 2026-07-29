"""
Tests for the tabular transformation pipeline.

Verifies that the pipeline produces correct output when run on hidden
data with multi-table joins, duplicate pivot keys, and type coercion.
"""

import json
import os
import subprocess
import shutil

EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"
HIDDEN_CONFIG_PATH = "/tests/eval_config_hidden.json"
PIPELINE_PATH = "/app/pipeline.py"
VISIBLE_CONFIG_PATH = "/app/transform_config.json"


def _run_pipeline_on_hidden_data():
    """Run the pipeline on hidden test data and return the output."""
    shutil.copy(HIDDEN_CONFIG_PATH, VISIBLE_CONFIG_PATH)
    result = subprocess.run(
        ["python3", PIPELINE_PATH, VISIBLE_CONFIG_PATH, ACTUAL_OUTPUT_PATH],
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"
    with open(ACTUAL_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def _load_expected():
    """Load expected output."""
    with open(EXPECTED_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def _approx_equal(a, b, rel_tol=1e-4):
    """Check approximate equality with relative tolerance."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == 0 and b == 0:
            return True
        return abs(a - b) <= rel_tol * max(abs(a), abs(b))
    return a == b


class TestPipelineOutput:
    """Test suite for tabular transformation pipeline correctness."""

    def setup_method(self):
        """Set up test fixtures by running the pipeline on hidden data."""
        self.actual = _run_pipeline_on_hidden_data()
        self.expected = _load_expected()

    def test_output_file_exists(self):
        """Verify that the pipeline produces an output.json file."""
        assert os.path.exists(ACTUAL_OUTPUT_PATH)

    def test_output_has_required_sections(self):
        """Verify output has metadata and data sections."""
        assert 'metadata' in self.actual
        assert 'data' in self.actual

    def test_row_count(self):
        """Verify the correct number of output rows."""
        assert len(self.actual['data']) == len(self.expected['data']), \
            f"Row count: got {len(self.actual['data'])}, expected {len(self.expected['data'])}"

    def test_metadata_row_count(self):
        """Verify metadata reports correct row count."""
        assert self.actual['metadata']['row_count'] == self.expected['metadata']['row_count']

    def test_source_tables(self):
        """Verify all source tables are recorded in metadata."""
        assert set(self.actual['metadata']['source_tables']) == \
            set(self.expected['metadata']['source_tables'])

    def test_transformations_applied(self):
        """Verify the correct sequence of transformations was applied."""
        assert self.actual['metadata']['transformations_applied'] == \
            self.expected['metadata']['transformations_applied']

    def test_product_ids(self):
        """Verify all expected product IDs are present in output."""
        actual_ids = sorted([row.get('product_id') for row in self.actual['data']])
        expected_ids = sorted([row.get('product_id') for row in self.expected['data']])
        assert actual_ids == expected_ids, \
            f"Product IDs: got {actual_ids}, expected {expected_ids}"

    def test_product_id_types(self):
        """Verify product IDs have correct type after coercion."""
        for row in self.actual['data']:
            pid = row.get('product_id')
            assert isinstance(pid, int), \
                f"product_id should be int, got {type(pid).__name__}: {pid}"

    def test_weighted_cost_values(self):
        """Verify weighted cost reflects summed pivot values multiplied by base price."""
        actual_by_id = {row['product_id']: row for row in self.actual['data']}
        expected_by_id = {row['product_id']: row for row in self.expected['data']}

        for pid in expected_by_id:
            assert pid in actual_by_id, f"Missing product_id {pid}"
            actual_val = actual_by_id[pid].get('weighted_cost')
            expected_val = expected_by_id[pid]['weighted_cost']
            assert actual_val is not None, \
                f"weighted_cost is None for product {pid}"
            assert _approx_equal(actual_val, expected_val), \
                f"weighted_cost for {pid}: got {actual_val}, expected {expected_val}"

    def test_length_cost_values(self):
        """Verify length cost values reflect joined and pivoted data correctly."""
        actual_by_id = {row['product_id']: row for row in self.actual['data']}
        expected_by_id = {row['product_id']: row for row in self.expected['data']}

        for pid in expected_by_id:
            actual_val = actual_by_id[pid].get('length_cost')
            expected_val = expected_by_id[pid]['length_cost']
            assert actual_val is not None, \
                f"length_cost is None for product {pid}"
            assert _approx_equal(actual_val, expected_val), \
                f"length_cost for {pid}: got {actual_val}, expected {expected_val}"

    def test_sort_order(self):
        """Verify output rows are sorted correctly by product_id descending."""
        ids = [row['product_id'] for row in self.actual['data']]
        assert ids == sorted(ids, reverse=True), \
            f"Expected descending sort, got: {ids}"

    def test_no_null_values_in_aggregates(self):
        """Verify no unexpected null values in computed columns."""
        for row in self.actual['data']:
            for col in ['weighted_cost', 'length_cost']:
                assert row.get(col) is not None, \
                    f"Unexpected None in {col} for product {row.get('product_id')}"
