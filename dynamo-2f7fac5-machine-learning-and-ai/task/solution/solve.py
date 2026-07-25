"""
Oracle solution for model evaluation pipeline.

Patches three cross-module data-flow bugs in pipeline.py:
1. Calibration receives train_labels instead of eval_labels
2. Cross-validation uses overall class weights instead of per-fold weights
3. Weighted F1 computes scores in alphabetical order but pairs with prevalence-order weights
"""

import subprocess
import sys


def patch_pipeline():
    """Apply string replacement patches to fix all three bugs."""
    pipeline_path = "/app/pipeline.py"

    with open(pipeline_path, 'r') as f:
        content = f.read()

    # Bug 1 fix: Pass eval_labels to calibration instead of train_labels
    content = content.replace(
        "cal_results = calibration.compute_calibration_metrics(\n"
        "        eval_predictions, train_labels, positive_class, cal_params['n_bins'])",
        "cal_results = calibration.compute_calibration_metrics(\n"
        "        eval_predictions, eval_labels, positive_class, cal_params['n_bins'])"
    )

    # Bug 2 fix: Compute per-fold weights instead of using overall class_weights
    # Replace the fold scoring section in _run_cross_validation
    content = content.replace(
        "        # Score this fold using the overall class weights for consistency\n"
        "        fold_score = cross_validation.score_fold(\n"
        "            fold_preds, fold_labels, classes, class_weights)",
        "        # Score this fold using per-fold class weights\n"
        "        fold_weights = metrics.compute_class_weights(fold_labels, classes)\n"
        "        fold_score = cross_validation.score_fold(\n"
        "            fold_preds, fold_labels, classes, fold_weights)"
    )

    # Bug 3 fix: Use prevalence-ordered scores to match prevalence-ordered weights
    content = content.replace(
        "    # Gather F1 scores in alphabetical order for consistent reporting\n"
        "    sorted_classes = sorted(classes)\n"
        "    sorted_f1_scores = [per_class_metrics[cls]['f1'] for cls in sorted_classes]\n"
        "    # Weights are computed in prevalence order from the distribution\n"
        "    prevalence_weights = [overall_class_weights[classes.index(cls)] for cls in prevalence_order]\n"
        "    weighted_f1 = metrics.compute_weighted_average(sorted_f1_scores, prevalence_weights)",
        "    # Gather F1 scores in prevalence order to match prevalence-ordered weights\n"
        "    prevalence_f1_scores = [per_class_metrics[cls]['f1'] for cls in prevalence_order]\n"
        "    # Weights are computed in prevalence order from the distribution\n"
        "    prevalence_weights = [overall_class_weights[classes.index(cls)] for cls in prevalence_order]\n"
        "    weighted_f1 = metrics.compute_weighted_average(prevalence_f1_scores, prevalence_weights)"
    )

    with open(pipeline_path, 'w') as f:
        f.write(content)

    print("All patches applied successfully.")


def run_pipeline():
    """Run the patched pipeline."""
    result = subprocess.run(
        ["python3", "/app/pipeline.py", "/app/eval_config.json", "/app/output.json"],
        capture_output=True, text=True
    )
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


if __name__ == "__main__":
    patch_pipeline()
    exit_code = run_pipeline()
    sys.exit(exit_code)
