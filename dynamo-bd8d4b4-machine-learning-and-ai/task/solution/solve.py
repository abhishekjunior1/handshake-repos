"""
Solution for model comparison benchmark pipeline.

Fixes two bugs in pipeline.py:
1. Aggregate computation uses raw scores instead of normalized scores
2. Confidence penalty pools CV across all datasets instead of averaging per-dataset CVs
"""

import subprocess


def fix_pipeline():
    """Apply patches to pipeline.py."""
    with open("/app/pipeline.py", "r") as f:
        content = f.read()

    # Fix 1: Use per_dataset_normalized instead of per_dataset_scores for aggregate
    old_aggregate = """    # Compute aggregate using per-dataset raw scores for full-precision
    # assessment that preserves the original measurement scale
    aggregate_perf = compute_aggregate_performance(
        per_dataset_scores, config["aggregation_method"]
    )"""

    new_aggregate = """    # Compute aggregate using normalized scores for scale-independent comparison
    aggregate_perf = compute_aggregate_performance(
        per_dataset_normalized, config["aggregation_method"]
    )"""

    content = content.replace(old_aggregate, new_aggregate)

    # Fix 2: Compute per-dataset CV and average instead of pooling all folds
    old_penalty = """    penalized = {}
    for model in models:
        # Pool all fold scores across datasets for unified stability
        # assessment that captures the model's global variance profile
        all_folds = []
        for dataset in datasets:
            fold_scores = get_fold_scores(results, model, dataset, primary_metric)
            all_folds.extend(fold_scores)

        mean_val = sum(all_folds) / len(all_folds)
        variance = sum((s - mean_val) ** 2 for s in all_folds) / (len(all_folds) - 1)
        std_val = math.sqrt(variance) if variance > 0 else 0.0
        cv = std_val / mean_val if mean_val > 0 else 0.0

        confidence = 1.0 / (1.0 + cv)
        penalized[model] = aggregate_perf[model] * confidence"""

    new_penalty = """    penalized = {}
    for model in models:
        # Compute per-dataset CV and average for scale-independent stability
        per_dataset_cvs = []
        for dataset in datasets:
            fold_scores = get_fold_scores(results, model, dataset, primary_metric)
            mean_val = sum(fold_scores) / len(fold_scores)
            variance = sum((s - mean_val) ** 2 for s in fold_scores) / (len(fold_scores) - 1)
            std_val = math.sqrt(variance) if variance > 0 else 0.0
            cv = std_val / mean_val if mean_val > 0 else 0.0
            per_dataset_cvs.append(cv)
        mean_cv = sum(per_dataset_cvs) / len(per_dataset_cvs)

        confidence = 1.0 / (1.0 + mean_cv)
        penalized[model] = aggregate_perf[model] * confidence"""

    content = content.replace(old_penalty, new_penalty)

    with open("/app/pipeline.py", "w") as f:
        f.write(content)

    print("Both bugs fixed in pipeline.py")


def run_pipeline():
    """Execute the fixed pipeline."""
    result = subprocess.run(
        ["python3", "/app/pipeline.py"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Pipeline error: {result.stderr}")
        raise RuntimeError("Pipeline execution failed")
    print(result.stdout)


if __name__ == "__main__":
    fix_pipeline()
    run_pipeline()
