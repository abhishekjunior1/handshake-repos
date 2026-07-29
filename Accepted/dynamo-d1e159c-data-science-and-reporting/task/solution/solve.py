"""Oracle solution - patches 3 bugs in the EDA pipeline."""

import subprocess


def patch_file(filepath, old, new):
    """Replace exact string in file."""
    with open(filepath, 'r') as f:
        content = f.read()
    assert old in content, f"Patch target not found in {filepath}: {repr(old[:80])}"
    content = content.replace(old, new, 1)
    with open(filepath, 'w') as f:
        f.write(content)


def main():
    # Bug 1 Fix: Move imputation BEFORE outlier detection
    # The buggy pipeline detects outliers on raw data (with NaN),
    # then imputes. Fixed: impute first, then detect outliers.
    patch_file(
        '/app/pipeline.py',
        """    # Step 1: Detect outliers on raw data before imputation
    # Run detection early to capture true distributional outliers
    # before any imputation alters the distribution shape
    outlier_results = {}
    cleaned_columns = {}
    for col in numeric_cols:
        iqr_result = detect_outliers_iqr(raw_columns[col])
        outlier_results[col] = iqr_result
        cleaned_columns[col] = clean_outliers(raw_columns[col], iqr_result['outlier_indices'])

    # Step 2: Impute missing values
    imputed_columns = {}
    for col in numeric_cols:
        imputed_columns[col] = impute_missing(cleaned_columns[col])""",
        """    # Step 1: Impute missing values first
    imputed_columns = {}
    for col in numeric_cols:
        imputed_columns[col] = impute_missing(raw_columns[col])

    # Step 2: Detect outliers on imputed data
    outlier_results = {}
    cleaned_columns = {}
    for col in numeric_cols:
        iqr_result = detect_outliers_iqr(imputed_columns[col])
        outlier_results[col] = iqr_result
        cleaned_columns[col] = clean_outliers(imputed_columns[col], iqr_result['outlier_indices'])"""
    )

    # Bug 2 Fix: Use cleaned columns for correlation instead of raw
    patch_file(
        '/app/pipeline.py',
        """    # Step 4: Compute correlations on numeric columns
    # Use raw numeric data for correlation to reflect the original
    # data relationships without outlier removal artifacts
    correlation_result = compute_correlation_matrix(raw_columns)""",
        """    # Step 4: Compute correlations on cleaned numeric columns
    correlation_result = compute_correlation_matrix(cleaned_columns)"""
    )

    # Bug 3 Fix: Group means should use valid_count as denominator
    patch_file(
        '/app/statistics.py',
        """        # Count all observations in the group for denominator
        group_counts[grp_key] += 1
        if val is not None:
            group_sums[grp_key] += val""",
        """        if val is not None:
            group_counts[grp_key] += 1
            group_sums[grp_key] += val"""
    )

    # Run the fixed pipeline
    subprocess.run(['python3', '/app/pipeline.py'], check=True)


if __name__ == '__main__':
    main()
