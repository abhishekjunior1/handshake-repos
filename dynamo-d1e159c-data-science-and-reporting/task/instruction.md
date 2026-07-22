An exploratory data analysis pipeline at `/app/pipeline.py` computes descriptive statistics, detects outliers, computes correlations, and performs group-wise aggregations on tabular datasets. It uses modules `/app/data_loader.py`, `/app/statistics.py`, `/app/outlier_detector.py`, `/app/correlations.py`, and `/app/report_generator.py`.

Run it with `python3 /app/pipeline.py`. It reads `/app/config.json` (which points to `/app/dataset.json`) and writes `/app/output.json`.

The pipeline handles datasets with mixed numeric and categorical columns. It imputes missing values with median, detects outliers using the IQR method, computes univariate statistics (mean, median, std, skewness, kurtosis, percentiles), Pearson and Spearman correlations, and group-wise aggregations by a categorical column.

The pipeline produces correct output on the current dataset but has bugs that cause incorrect results on datasets with missing values and extreme outliers. Find and fix the bugs so the pipeline handles all valid inputs correctly.

Do not rewrite from scratch — preserve the existing module structure and interfaces. The fixed pipeline will be tested on a different dataset than the one at `/app/dataset.json`.

Output: `/app/output.json` — a JSON object with keys:
- `univariate_statistics`: per-column descriptive statistics (count, missing, mean, median, std, skewness, kurtosis, min, max, percentiles)
- `outlier_detection`: per-column IQR bounds and detected outlier indices/values
- `correlations`: Pearson and Spearman correlation matrices between numeric columns
- `group_analysis`: per-group aggregations (count, valid_count, mean, std) for each numeric column

Processing conventions: outlier detection should run on data after missing value imputation (so quartile estimates are not corrupted by NaN). Correlations should be computed on outlier-cleaned columns (so extreme values do not dominate). Group means use valid (non-null) observation count as the denominator.
