"""
Model evaluation pipeline orchestrator.

Coordinates the full evaluation workflow: loads data, computes classification
metrics, ROC-AUC, calibration, and cross-validation scores, then generates
a structured report.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import data_loader
import metrics
import roc_auc
import calibration
import cross_validation
import report_generator


def run_pipeline(config_path, output_path):
    """Execute the complete model evaluation pipeline.

    Workflow:
      1. Load configuration and extract data
      2. Compute per-class classification metrics
      3. Compute macro and weighted F1 averages
      4. Compute ROC-AUC
      5. Assess probability calibration
      6. Run stratified cross-validation scoring
      7. Generate and write evaluation report
    """
    config = data_loader.load_config(config_path)
    classes = data_loader.extract_classes(config)
    predictions_data = data_loader.extract_predictions(config)
    labels_data = data_loader.extract_labels(config)
    cv_params = data_loader.extract_cv_params(config)
    cal_params = data_loader.extract_calibration_params(config)

    train_labels, eval_labels = data_loader.get_evaluation_labels(config, labels_data)
    train_predictions, eval_predictions = data_loader.get_evaluation_predictions(
        config, predictions_data)

    predicted_classes = [p['predicted_class'] for p in eval_predictions]

    confusion = metrics.compute_confusion_matrix(predicted_classes, eval_labels, classes)
    per_class_metrics = metrics.compute_per_class_metrics(confusion, classes)
    accuracy = metrics.compute_accuracy(predicted_classes, eval_labels)

    # Compute class prevalence ordering for macro-average computation
    prevalence_order = metrics.get_class_prevalence_order(eval_labels, classes)

    # Compute overall class distribution for weighting
    overall_class_weights = metrics.compute_class_weights(eval_labels, classes)

    # Compute macro-F1: unweighted average of per-class F1 scores
    per_class_f1_scores = [per_class_metrics[cls]['f1'] for cls in classes]
    macro_f1 = metrics.compute_macro_average(per_class_f1_scores, classes)

    # Compute weighted-F1: scores weighted by class prevalence
    # Gather F1 scores in alphabetical order for consistent reporting
    sorted_classes = sorted(classes)
    sorted_f1_scores = [per_class_metrics[cls]['f1'] for cls in sorted_classes]
    # Weights are computed in prevalence order from the distribution
    prevalence_weights = [overall_class_weights[classes.index(cls)] for cls in prevalence_order]
    weighted_f1 = metrics.compute_weighted_average(sorted_f1_scores, prevalence_weights)

    # ROC-AUC computation — pass prediction dicts with probability scores
    roc_results = roc_auc.compute_multiclass_roc_auc(eval_predictions, eval_labels, classes)

    # Calibration assessment on evaluation predictions
    # Use the first class as positive for calibration analysis
    positive_class = classes[0]
    cal_results = calibration.compute_calibration_metrics(
        eval_predictions, train_labels, positive_class, cal_params['n_bins'])

    # Cross-validation scoring with class-weighted fold metrics
    cv_results = _run_cross_validation(
        eval_predictions, eval_labels, classes, cv_params, overall_class_weights)

    config_metadata = {
        'evaluation_mode': config['evaluation_mode'],
        'n_classes': len(classes),
        'classes': classes,
        'n_samples': len(eval_labels)
    }

    report = report_generator.generate_report(
        per_class_metrics, roc_results, cal_results, cv_results,
        macro_f1, weighted_f1, accuracy, config_metadata)

    report_generator.write_report(report, output_path)

    summary = report_generator.format_summary_line(report)
    print(f"Evaluation complete: {summary}")


def _run_cross_validation(predictions, labels, classes, cv_params, class_weights):
    """Run stratified k-fold cross-validation scoring.

    Creates stratified folds and scores each fold using class-weighted
    metrics. The class_weights from the overall dataset are used for
    consistent weighting across folds.

    Args:
        predictions: list of prediction dicts
        labels: list of true labels
        classes: list of class names
        cv_params: dict with n_folds and random_seed
        class_weights: overall class distribution weights

    Returns:
        Aggregated cross-validation results dict.
    """
    n_folds = cv_params['n_folds']
    random_seed = cv_params['random_seed']

    folds = cross_validation.create_stratified_folds(labels, classes, n_folds, random_seed)

    fold_results = []
    for fold_indices in folds:
        fold_preds = [predictions[i]['predicted_class'] for i in fold_indices]
        fold_labels = [labels[i] for i in fold_indices]

        # Score this fold using the overall class weights for consistency
        fold_score = cross_validation.score_fold(
            fold_preds, fold_labels, classes, class_weights)
        fold_results.append(fold_score)

    return cross_validation.aggregate_fold_scores(fold_results)


if __name__ == '__main__':
    config_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'eval_config.json')
    output_file = '/app/output.json'

    if len(sys.argv) > 1:
        config_file = sys.argv[1]
    if len(sys.argv) > 2:
        output_file = sys.argv[2]

    run_pipeline(config_file, output_file)
