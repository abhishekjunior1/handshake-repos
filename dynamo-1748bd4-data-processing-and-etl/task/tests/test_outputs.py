"""
Tests for the weighted hierarchical rollup pipeline output.

Validates all output fields against expected results, including:
- Pipeline metadata and parameters
- Input summary statistics
- Product-level records with contribution scores and outlier adjustments
- Category-level hierarchical rollup aggregates
- Department-level hierarchical rollup aggregates
- Diagnostics (outlier detection, contribution stats, rollup summary, normalization)
"""

import json
import os
import math

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = '/app/output.json'
EXPECTED_PATH = os.path.join(TESTS_DIR, 'expected_output.json')


def load_json(path):
    """Load and return parsed JSON from the given file path."""
    with open(path, 'r') as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4, abs_tol=1e-8):
    """Check if two numeric values are approximately equal within tolerance."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == 0 and b == 0:
            return True
        return math.isclose(a, b, rel_tol=rel_tol, abs_tol=abs_tol)
    return a == b


def assert_records_match(actual_records, expected_records, level_name):
    """Assert that two lists of records match field-by-field with tolerance."""
    assert len(actual_records) == len(expected_records), \
        f"{level_name}: record count {len(actual_records)} != {len(expected_records)}"
    for i, (ar, er) in enumerate(zip(actual_records, expected_records)):
        for key in er:
            assert key in ar, f"{level_name} record {i} missing key: {key}"
            assert approx_equal(ar[key], er[key]), \
                f"{level_name} record {i}, '{key}': {ar[key]} != {er[key]}"


class TestFormatVersion:
    """Tests for top-level format version field."""

    def test_format_version(self):
        """Verify the output format_version matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['format_version'] == expected['format_version']


class TestPipelineMetadata:
    """Tests for the pipeline metadata section."""

    def test_pipeline_name(self):
        """Verify pipeline name matches expected value."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['pipeline']['pipeline_name'] == expected['pipeline']['pipeline_name']

    def test_pipeline_version(self):
        """Verify pipeline version matches expected value."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['pipeline']['version'] == expected['pipeline']['version']

    def test_pipeline_parameters(self):
        """Verify all pipeline parameters match expected values."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_params = actual['pipeline']['parameters']
        expected_params = expected['pipeline']['parameters']
        assert approx_equal(actual_params['half_life_days'], expected_params['half_life_days'])
        assert approx_equal(actual_params['outlier_threshold'], expected_params['outlier_threshold'])
        assert approx_equal(actual_params['dampening_factor'], expected_params['dampening_factor'])
        assert actual_params['reference_date'] == expected_params['reference_date']
        assert actual_params['hierarchy_levels'] == expected_params['hierarchy_levels']
        assert actual_params['value_columns'] == expected_params['value_columns']


class TestInputSummary:
    """Tests for the input_summary section."""

    def test_record_count(self):
        """Verify input record count matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['input_summary']['record_count'] == expected['input_summary']['record_count']

    def test_date_range(self):
        """Verify input date range min and max match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['input_summary']['date_range'] == expected['input_summary']['date_range']

    def test_hierarchy_validation(self):
        """Verify hierarchy validation results match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_hv = actual['input_summary']['hierarchy_validation']
        expected_hv = expected['input_summary']['hierarchy_validation']
        assert actual_hv['is_valid'] == expected_hv['is_valid']
        for level in expected_hv['levels']:
            assert level in actual_hv['levels'], f"Missing hierarchy level: {level}"
            for key in expected_hv['levels'][level]:
                assert approx_equal(
                    actual_hv['levels'][level][key],
                    expected_hv['levels'][level][key]
                ), f"Hierarchy {level}.{key} mismatch"

    def test_recency_score(self):
        """Verify the computed recency score matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert approx_equal(
            actual['input_summary']['recency_score'],
            expected['input_summary']['recency_score']
        )

    def test_weight_statistics(self):
        """Verify all weight statistics (mean, median, std, min, max, cv) match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_ws = actual['input_summary']['weight_statistics']
        expected_ws = expected['input_summary']['weight_statistics']
        for key in expected_ws:
            assert approx_equal(actual_ws[key], expected_ws[key]), \
                f"weight_statistics.{key}: {actual_ws[key]} != {expected_ws[key]}"


class TestProductResults:
    """Tests for the product-level results section."""

    def test_product_record_count(self):
        """Verify the number of product-level records matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['results']['product']['record_count'] == \
            expected['results']['product']['record_count']

    def test_product_revenue_values(self):
        """Verify revenue values for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['revenue'], er['revenue']), \
                f"Product {i} ({er.get('product', '')}): revenue {ar['revenue']} != {er['revenue']}"

    def test_product_effective_weights(self):
        """Verify effective_weight for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['effective_weight'], er['effective_weight']), \
                f"Product {i}: effective_weight {ar['effective_weight']} != {er['effective_weight']}"

    def test_product_contribution_scores(self):
        """Verify contribution_score for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['contribution_score'], er['contribution_score']), \
                f"Product {i}: contribution_score {ar['contribution_score']} != {er['contribution_score']}"

    def test_product_normalized_scores(self):
        """Verify normalized_score for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['normalized_score'], er['normalized_score']), \
                f"Product {i}: normalized_score {ar['normalized_score']} != {er['normalized_score']}"

    def test_product_outlier_flags(self):
        """Verify is_outlier flags for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert ar['is_outlier'] == er['is_outlier'], \
                f"Product {i}: is_outlier {ar['is_outlier']} != {er['is_outlier']}"

    def test_product_modified_z_scores(self):
        """Verify modified_z_score for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['modified_z_score'], er['modified_z_score']), \
                f"Product {i}: modified_z_score {ar['modified_z_score']} != {er['modified_z_score']}"

    def test_product_adjusted_revenue(self):
        """Verify adjusted_revenue for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['adjusted_revenue'], er['adjusted_revenue']), \
                f"Product {i}: adjusted_revenue {ar['adjusted_revenue']} != {er['adjusted_revenue']}"

    def test_product_share_pct(self):
        """Verify share_pct for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['share_pct'], er['share_pct']), \
                f"Product {i}: share_pct {ar['share_pct']} != {er['share_pct']}"

    def test_product_normalized_value(self):
        """Verify normalized_value for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['normalized_value'], er['normalized_value']), \
                f"Product {i}: normalized_value {ar['normalized_value']} != {er['normalized_value']}"

    def test_product_dampened_share(self):
        """Verify revenue_dampened_share for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['revenue_dampened_share'], er['revenue_dampened_share']), \
                f"Product {i}: revenue_dampened_share {ar['revenue_dampened_share']} != {er['revenue_dampened_share']}"

    def test_product_group_total_weighted_value(self):
        """Verify group_total_weighted_value for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['group_total_weighted_value'], er['group_total_weighted_value']), \
                f"Product {i}: group_total_weighted_value mismatch"

    def test_product_total_basis(self):
        """Verify total_basis for all product records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['product']['records']
        expected_recs = expected['results']['product']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['total_basis'], er['total_basis']), \
                f"Product {i}: total_basis {ar['total_basis']} != {er['total_basis']}"

    def test_product_all_fields(self):
        """Verify all fields for all product records match expected (comprehensive check)."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert_records_match(
            actual['results']['product']['records'],
            expected['results']['product']['records'],
            "product"
        )


class TestCategoryResults:
    """Tests for the category-level rollup results."""

    def test_category_record_count(self):
        """Verify the number of category-level records matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['results']['category']['record_count'] == \
            expected['results']['category']['record_count']

    def test_category_revenue(self):
        """Verify revenue values for all category records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['category']['records']
        expected_recs = expected['results']['category']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['revenue'], er['revenue']), \
                f"Category {er.get('category', i)}: revenue {ar['revenue']} != {er['revenue']}"

    def test_category_group_weight_sum(self):
        """Verify group_weight_sum for all category records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['category']['records']
        expected_recs = expected['results']['category']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['group_weight_sum'], er['group_weight_sum']), \
                f"Category {er.get('category', i)}: group_weight_sum mismatch"

    def test_category_group_weight_mean(self):
        """Verify group_weight_mean for all category records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['category']['records']
        expected_recs = expected['results']['category']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['group_weight_mean'], er['group_weight_mean']), \
                f"Category {er.get('category', i)}: group_weight_mean mismatch"

    def test_category_share_pct(self):
        """Verify share_pct for all category records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['category']['records']
        expected_recs = expected['results']['category']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['share_pct'], er['share_pct']), \
                f"Category {er.get('category', i)}: share_pct {ar['share_pct']} != {er['share_pct']}"

    def test_category_normalized_value(self):
        """Verify normalized_value for all category records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['category']['records']
        expected_recs = expected['results']['category']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['normalized_value'], er['normalized_value']), \
                f"Category {er.get('category', i)}: normalized_value mismatch"

    def test_category_dampened_share(self):
        """Verify revenue_dampened_share for all category records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['category']['records']
        expected_recs = expected['results']['category']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['revenue_dampened_share'], er['revenue_dampened_share']), \
                f"Category {er.get('category', i)}: revenue_dampened_share mismatch"

    def test_category_all_fields(self):
        """Verify all fields for all category records match expected (comprehensive check)."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert_records_match(
            actual['results']['category']['records'],
            expected['results']['category']['records'],
            "category"
        )


class TestDepartmentResults:
    """Tests for the department-level rollup results."""

    def test_department_record_count(self):
        """Verify the number of department-level records matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['results']['department']['record_count'] == \
            expected['results']['department']['record_count']

    def test_department_revenue(self):
        """Verify revenue values for all department records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['department']['records']
        expected_recs = expected['results']['department']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['revenue'], er['revenue']), \
                f"Department {er.get('department', i)}: revenue {ar['revenue']} != {er['revenue']}"

    def test_department_group_weight_sum(self):
        """Verify group_weight_sum for all department records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['department']['records']
        expected_recs = expected['results']['department']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['group_weight_sum'], er['group_weight_sum']), \
                f"Department {er.get('department', i)}: group_weight_sum mismatch"

    def test_department_share_pct(self):
        """Verify share_pct for all department records match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_recs = actual['results']['department']['records']
        expected_recs = expected['results']['department']['records']
        for i, (ar, er) in enumerate(zip(actual_recs, expected_recs)):
            assert approx_equal(ar['share_pct'], er['share_pct']), \
                f"Department {er.get('department', i)}: share_pct mismatch"

    def test_department_all_fields(self):
        """Verify all fields for all department records match expected (comprehensive check)."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert_records_match(
            actual['results']['department']['records'],
            expected['results']['department']['records'],
            "department"
        )


class TestDiagnosticsOutlier:
    """Tests for the outlier detection diagnostics."""

    def test_outlier_total_records(self):
        """Verify total_records in outlier diagnostics matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['diagnostics']['outlier_detection']['total_records'] == \
            expected['diagnostics']['outlier_detection']['total_records']

    def test_outlier_count(self):
        """Verify outlier_count in diagnostics matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['diagnostics']['outlier_detection']['outlier_count'] == \
            expected['diagnostics']['outlier_detection']['outlier_count']

    def test_outlier_rate(self):
        """Verify outlier_rate in diagnostics matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert approx_equal(
            actual['diagnostics']['outlier_detection']['outlier_rate'],
            expected['diagnostics']['outlier_detection']['outlier_rate']
        )

    def test_outlier_threshold(self):
        """Verify threshold_used in outlier diagnostics matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert approx_equal(
            actual['diagnostics']['outlier_detection']['threshold_used'],
            expected['diagnostics']['outlier_detection']['threshold_used']
        )

    def test_outlier_median_and_mad(self):
        """Verify median and MAD values in outlier diagnostics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_od = actual['diagnostics']['outlier_detection']
        expected_od = expected['diagnostics']['outlier_detection']
        assert approx_equal(actual_od['median'], expected_od['median'])
        assert approx_equal(actual_od['mad'], expected_od['mad'])


class TestDiagnosticsContribution:
    """Tests for the contribution statistics diagnostics."""

    def test_contribution_count(self):
        """Verify contribution statistics count matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert actual['diagnostics']['contribution_statistics']['count'] == \
            expected['diagnostics']['contribution_statistics']['count']

    def test_contribution_mean(self):
        """Verify contribution statistics mean matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert approx_equal(
            actual['diagnostics']['contribution_statistics']['mean'],
            expected['diagnostics']['contribution_statistics']['mean']
        )

    def test_contribution_gini(self):
        """Verify contribution Gini coefficient matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert approx_equal(
            actual['diagnostics']['contribution_statistics']['gini_coefficient'],
            expected['diagnostics']['contribution_statistics']['gini_coefficient']
        )

    def test_contribution_min_max(self):
        """Verify contribution min and max values match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_cs = actual['diagnostics']['contribution_statistics']
        expected_cs = expected['diagnostics']['contribution_statistics']
        assert approx_equal(actual_cs['min'], expected_cs['min'])
        assert approx_equal(actual_cs['max'], expected_cs['max'])

    def test_contribution_top_concentration(self):
        """Verify top_concentration metric matches expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        assert approx_equal(
            actual['diagnostics']['contribution_statistics']['top_concentration'],
            expected['diagnostics']['contribution_statistics']['top_concentration']
        )


class TestDiagnosticsRollupSummary:
    """Tests for the rollup summary diagnostics."""

    def test_product_rollup_summary(self):
        """Verify product-level rollup summary statistics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_rs = actual['diagnostics']['rollup_summary']['product']
        expected_rs = expected['diagnostics']['rollup_summary']['product']
        for key in expected_rs:
            assert approx_equal(actual_rs[key], expected_rs[key]), \
                f"rollup_summary.product.{key}: {actual_rs[key]} != {expected_rs[key]}"

    def test_category_rollup_summary(self):
        """Verify category-level rollup summary statistics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_rs = actual['diagnostics']['rollup_summary']['category']
        expected_rs = expected['diagnostics']['rollup_summary']['category']
        for key in expected_rs:
            assert approx_equal(actual_rs[key], expected_rs[key]), \
                f"rollup_summary.category.{key}: {actual_rs[key]} != {expected_rs[key]}"

    def test_department_rollup_summary(self):
        """Verify department-level rollup summary statistics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_rs = actual['diagnostics']['rollup_summary']['department']
        expected_rs = expected['diagnostics']['rollup_summary']['department']
        for key in expected_rs:
            assert approx_equal(actual_rs[key], expected_rs[key]), \
                f"rollup_summary.department.{key}: {actual_rs[key]} != {expected_rs[key]}"


class TestDiagnosticsNormalization:
    """Tests for the normalization diagnostics."""

    def test_product_normalization(self):
        """Verify product-level normalization diagnostics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_n = actual['diagnostics']['normalization']['product']
        expected_n = expected['diagnostics']['normalization']['product']
        assert approx_equal(actual_n['share_total_pct'], expected_n['share_total_pct'])
        assert actual_n['share_valid'] == expected_n['share_valid']
        assert approx_equal(actual_n['revenue_dampening_impact'], expected_n['revenue_dampening_impact'])

    def test_category_normalization(self):
        """Verify category-level normalization diagnostics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_n = actual['diagnostics']['normalization']['category']
        expected_n = expected['diagnostics']['normalization']['category']
        assert approx_equal(actual_n['share_total_pct'], expected_n['share_total_pct'])
        assert actual_n['share_valid'] == expected_n['share_valid']
        assert approx_equal(actual_n['revenue_dampening_impact'], expected_n['revenue_dampening_impact'])

    def test_department_normalization(self):
        """Verify department-level normalization diagnostics match expected."""
        actual = load_json(OUTPUT_PATH)
        expected = load_json(EXPECTED_PATH)
        actual_n = actual['diagnostics']['normalization']['department']
        expected_n = expected['diagnostics']['normalization']['department']
        assert approx_equal(actual_n['share_total_pct'], expected_n['share_total_pct'])
        assert actual_n['share_valid'] == expected_n['share_valid']
        assert approx_equal(actual_n['revenue_dampening_impact'], expected_n['revenue_dampening_impact'])
