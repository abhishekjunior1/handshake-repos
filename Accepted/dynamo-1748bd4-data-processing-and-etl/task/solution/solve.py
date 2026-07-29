"""
Solution script for the weighted hierarchical rollup pipeline.

Fixes 3 bugs across 3 files:
1. pipeline.py: Pass outlier_adjusted_values to hierarchy_aggregator instead of raw_values
2. contribution_scorer.py: Use per-group min/max for min-max normalization instead of global
3. hierarchy_aggregator.py: Divide weighted sum by sum_of_weights instead of count
"""

import subprocess


def fix_pipeline():
    """Fix Bug 1: hierarchy aggregation should use adjusted_revenue, not raw revenue."""
    filepath = '/app/pipeline.py'
    with open(filepath, 'r') as f:
        content = f.read()

    old = """        # Use raw revenue values to preserve authentic data lineage and
        # prevent adjustment artifacts from propagating up the hierarchy
        hier_record["revenue"] = record["revenue"]"""

    assert old in content, f"Bug 1 old string not found in {filepath}"
    
    new = """        # Use outlier-adjusted revenue for hierarchical aggregation
        # to prevent extreme values from distorting group aggregates
        hier_record["revenue"] = record["adjusted_revenue"]"""

    content = content.replace(old, new, 1)

    with open(filepath, 'w') as f:
        f.write(content)
    print("Fixed Bug 1: pipeline.py - use adjusted_revenue for hierarchy input")


def fix_contribution_scorer():
    """Fix Bug 2: use per-group min/max for min-max normalization instead of global."""
    filepath = '/app/contribution_scorer.py'
    with open(filepath, 'r') as f:
        content = f.read()

    old = """    if method == 'min_max':
        # Global normalization range ensures cross-group comparability
        # on a unified scale. This approach uses the global minimum and
        # maximum across all groups to establish the normalization bounds,
        # ensuring consistent interpretation of normalized values regardless
        # of group membership.
        all_values = [float(s[score_field]) for s in scores]
        global_min = min(all_values)
        global_max = max(all_values)
        value_range = global_max - global_min

        for record in normalized:
            raw_score = float(record[score_field])
            if abs(value_range) < EPSILON:
                record["normalized_score"] = 0.5
            else:
                record["normalized_score"] = (raw_score - global_min) / value_range"""

    assert old in content, f"Bug 2 old string not found in {filepath}"

    new = """    if method == 'min_max':
        # Per-group normalization ensures each group's scores are scaled
        # relative to that group's own range, providing meaningful within-group
        # comparison of contribution magnitudes.
        groups = {}
        for i, s in enumerate(scores):
            g = s.get(group_key, '__all__') if group_key else '__all__'
            if g not in groups:
                groups[g] = []
            groups[g].append(i)

        for g, indices in groups.items():
            group_values = [float(scores[i][score_field]) for i in indices]
            group_min = min(group_values)
            group_max = max(group_values)
            value_range = group_max - group_min

            for idx in indices:
                raw_score = float(scores[idx][score_field])
                if abs(value_range) < EPSILON:
                    normalized[idx]["normalized_score"] = 0.5
                else:
                    normalized[idx]["normalized_score"] = (raw_score - group_min) / value_range"""

    content = content.replace(old, new, 1)

    with open(filepath, 'w') as f:
        f.write(content)
    print("Fixed Bug 2: contribution_scorer.py - per-group min-max normalization")


def fix_hierarchy_aggregator():
    """Fix Bug 3: divide weighted sum by sum_of_weights instead of count."""
    filepath = '/app/hierarchy_aggregator.py'
    with open(filepath, 'r') as f:
        content = f.read()

    old = """            # Arithmetic normalization by observation count for unbiased
            # group estimates independent of weight magnitude
            agg_record[col] = weighted_sum / n if n > 0 else 0.0"""

    assert old in content, f"Bug 3 old string not found in {filepath}"

    new = """            # Normalize by sum of weights for proper weighted mean
            weight_sum = sum(float(r.get(weight_col, 1.0)) for r in group_records)
            agg_record[col] = weighted_sum / weight_sum if weight_sum > 0 else 0.0"""

    content = content.replace(old, new, 1)

    with open(filepath, 'w') as f:
        f.write(content)
    print("Fixed Bug 3: hierarchy_aggregator.py - divide by sum_of_weights")


if __name__ == '__main__':
    fix_pipeline()
    fix_contribution_scorer()
    fix_hierarchy_aggregator()
    print("\nAll 3 bugs fixed. Running pipeline...")
    subprocess.run(['python3', '/app/pipeline.py', 'input.json', 'output.json'], check=True)
    print("Pipeline completed successfully.")
