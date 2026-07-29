"""EDA Pipeline - Main orchestrator.

Performs exploratory data analysis on a tabular dataset:
1. Load data and detect column types
2. Impute missing values (median for numeric)
3. Detect outliers (IQR method)
4. Compute univariate statistics
5. Compute correlations
6. Perform group-wise analysis
7. Generate report

Usage:
    python3 pipeline.py [config_file] [output_file]
"""

import sys
import json

from data_loader import load_dataset, detect_column_types, get_column_values
from statistics import compute_univariate_stats, compute_group_means, compute_group_aggregations
from outlier_detector import detect_outliers_iqr, detect_outliers_zscore, clean_outliers
from correlations import compute_correlation_matrix
from report_generator import generate_report, write_report


def impute_missing(values, method='median'):
    """Impute missing values with median."""
    valid = [v for v in values if v is not None]
    if not valid:
        return values
    sorted_valid = sorted(valid)
    n = len(sorted_valid)
    if n % 2 == 1:
        median = sorted_valid[n // 2]
    else:
        median = (sorted_valid[n // 2 - 1] + sorted_valid[n // 2]) / 2.0
    return [v if v is not None else median for v in values]


def run_pipeline(config_path: str, output_path: str) -> None:
    """Execute the full EDA pipeline."""

    with open(config_path, 'r') as f:
        config = json.load(f)

    dataset = load_dataset(config['dataset_path'])
    columns = dataset['columns']
    data = dataset['data']
    group_col = config.get('group_column', None)

    col_types = detect_column_types(columns, data)
    numeric_cols = [c for c in columns if col_types[c] == 'numeric']

    # Extract raw column values
    raw_columns = {}
    for col in numeric_cols:
        raw_columns[col] = get_column_values(data, columns, col)

    # Step 1: Detect outliers on raw data before imputation
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
        imputed_columns[col] = impute_missing(cleaned_columns[col])

    # Step 3: Compute univariate statistics on imputed data
    univariate = {}
    for col in numeric_cols:
        univariate[col] = compute_univariate_stats(imputed_columns[col])

    # Step 4: Compute correlations on numeric columns
    # Use raw numeric data for correlation to reflect the original
    # data relationships without outlier removal artifacts
    correlation_result = compute_correlation_matrix(raw_columns)

    # Step 5: Group-wise analysis
    group_analysis = {}
    if group_col and group_col in columns:
        group_values = get_column_values(data, columns, group_col)
        for col in numeric_cols:
            group_analysis[col] = compute_group_aggregations(
                raw_columns[col], group_values
            )

    # Step 6: Generate report
    metadata = {
        'n_rows': len(data),
        'n_columns': len(columns),
        'numeric_columns': numeric_cols,
        'categorical_columns': [c for c in columns if col_types[c] == 'categorical'],
        'group_column': group_col
    }

    report = generate_report(univariate, outlier_results, correlation_result,
                             group_analysis, metadata)
    write_report(report, output_path)


def main():
    config_path = sys.argv[1] if len(sys.argv) > 1 else '/app/config.json'
    output_path = sys.argv[2] if len(sys.argv) > 2 else '/app/output.json'
    run_pipeline(config_path, output_path)


if __name__ == '__main__':
    main()
