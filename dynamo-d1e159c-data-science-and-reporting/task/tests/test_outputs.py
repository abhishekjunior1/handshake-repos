"""Tests for the EDA pipeline output.

Verifies correct handling of missing values, outliers, correlations,
and group-wise aggregations on data with NaN and extreme values.
"""

import json
import os
import math

EXPECTED_PATH = "/tests/expected_output.json"
OUTPUT_PATH = "/app/output.json"


def load_output():
    """Load the pipeline output JSON."""
    assert os.path.exists(OUTPUT_PATH), f"Output not found at {OUTPUT_PATH}"
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output JSON."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def test_output_exists():
    """Verify the pipeline produces output.json."""
    assert os.path.exists(OUTPUT_PATH)


def test_output_structure():
    """Verify output has all required top-level keys."""
    output = load_output()
    for key in ['univariate_statistics', 'outlier_detection', 'correlations', 'group_analysis', 'metadata']:
        assert key in output, f"Missing key: {key}"


def test_outlier_counts():
    """Verify correct number of outliers detected per column."""
    output = load_output()
    expected = load_expected()
    for col in expected['outlier_detection']:
        assert output['outlier_detection'][col]['n_outliers'] == expected['outlier_detection'][col]['n_outliers'], (
            f"Outlier count wrong for {col}: got {output['outlier_detection'][col]['n_outliers']}, "
            f"expected {expected['outlier_detection'][col]['n_outliers']}"
        )


def test_outlier_bounds():
    """Verify IQR bounds are computed correctly (after imputation)."""
    output = load_output()
    expected = load_expected()
    for col in expected['outlier_detection']:
        out_lower = output['outlier_detection'][col]['lower_bound']
        exp_lower = expected['outlier_detection'][col]['lower_bound']
        assert abs(out_lower - exp_lower) < 0.01, (
            f"{col} lower bound wrong: got {out_lower}, expected {exp_lower}"
        )
        out_upper = output['outlier_detection'][col]['upper_bound']
        exp_upper = expected['outlier_detection'][col]['upper_bound']
        assert abs(out_upper - exp_upper) < 0.01, (
            f"{col} upper bound wrong: got {out_upper}, expected {exp_upper}"
        )


def test_pearson_correlations():
    """Verify Pearson correlation matrix computed on cleaned data."""
    output = load_output()
    expected = load_expected()
    for col_a in expected['correlations']['pearson']:
        for col_b in expected['correlations']['pearson'][col_a]:
            exp_val = expected['correlations']['pearson'][col_a][col_b]
            out_val = output['correlations']['pearson'][col_a][col_b]
            if exp_val is None:
                assert out_val is None
            else:
                assert abs(out_val - exp_val) < 0.001, (
                    f"Pearson[{col_a}][{col_b}] wrong: got {out_val}, expected {exp_val}"
                )


def test_spearman_correlations():
    """Verify Spearman correlation matrix computed on cleaned data."""
    output = load_output()
    expected = load_expected()
    for col_a in expected['correlations']['spearman']:
        for col_b in expected['correlations']['spearman'][col_a]:
            exp_val = expected['correlations']['spearman'][col_a][col_b]
            out_val = output['correlations']['spearman'][col_a][col_b]
            if exp_val is None:
                assert out_val is None
            else:
                assert abs(out_val - exp_val) < 0.001, (
                    f"Spearman[{col_a}][{col_b}] wrong: got {out_val}, expected {exp_val}"
                )


def test_group_means():
    """Verify group means use valid_count as denominator (not total_count)."""
    output = load_output()
    expected = load_expected()
    for col in expected['group_analysis']:
        for grp in expected['group_analysis'][col]:
            exp_mean = expected['group_analysis'][col][grp]['mean']
            out_mean = output['group_analysis'][col][grp]['mean']
            if exp_mean is None:
                assert out_mean is None
            else:
                assert abs(out_mean - exp_mean) < 0.001, (
                    f"Group mean [{col}][{grp}] wrong: got {out_mean}, expected {exp_mean}"
                )


def test_group_valid_counts():
    """Verify valid_count is correctly reported per group."""
    output = load_output()
    expected = load_expected()
    for col in expected['group_analysis']:
        for grp in expected['group_analysis'][col]:
            assert output['group_analysis'][col][grp]['valid_count'] == expected['group_analysis'][col][grp]['valid_count'], (
                f"valid_count [{col}][{grp}] wrong"
            )


def test_univariate_statistics():
    """Verify univariate statistics are computed on properly processed data."""
    output = load_output()
    expected = load_expected()
    for col in expected['univariate_statistics']:
        for stat in ['mean', 'median', 'std']:
            exp_val = expected['univariate_statistics'][col][stat]
            out_val = output['univariate_statistics'][col][stat]
            if exp_val is None:
                continue
            assert abs(out_val - exp_val) < 0.01, (
                f"{col}.{stat} wrong: got {out_val}, expected {exp_val}"
            )


def test_full_output_match():
    """Verify complete output matches expected."""
    output = load_output()
    expected = load_expected()
    assert output == expected, "Full output does not match expected."
