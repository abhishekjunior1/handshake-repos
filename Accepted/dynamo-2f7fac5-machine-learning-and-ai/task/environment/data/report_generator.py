"""
Report generator module for model evaluation pipeline.

Assembles all computed metrics into a structured JSON evaluation report
with standardized formatting and metadata.
"""

import json


def generate_report(classification_metrics, roc_auc_results, calibration_results,
                    cv_results, macro_f1, weighted_f1, accuracy, config_metadata):
    """Generate the full evaluation report as a structured dictionary.

    Combines results from all evaluation modules into a single report
    suitable for JSON serialization.

    Args:
        classification_metrics: per-class precision/recall/F1 dict
        roc_auc_results: ROC-AUC results dict
        calibration_results: calibration assessment dict
        cv_results: cross-validation results dict
        macro_f1: macro-averaged F1 score
        weighted_f1: weighted-averaged F1 score
        accuracy: overall accuracy
        config_metadata: dict with evaluation configuration info

    Returns:
        Complete report dictionary.
    """
    report = {
        'evaluation_metadata': {
            'evaluation_mode': config_metadata.get('evaluation_mode', 'unknown'),
            'n_classes': config_metadata.get('n_classes', 0),
            'classes': config_metadata.get('classes', []),
            'n_samples_evaluated': config_metadata.get('n_samples', 0)
        },
        'classification_report': {
            'per_class': _format_per_class_metrics(classification_metrics),
            'macro_f1': round(macro_f1, 6),
            'weighted_f1': round(weighted_f1, 6),
            'accuracy': round(accuracy, 6)
        },
        'roc_auc': {
            'macro_auc': roc_auc_results.get('macro_auc', 0.0),
            'per_class_auc': roc_auc_results.get('per_class_auc', {})
        },
        'calibration': {
            'ece': calibration_results.get('ece', 0.0),
            'mce': calibration_results.get('mce', 0.0),
            'n_bins_used': len(calibration_results.get('bins', [])),
            'positive_class': calibration_results.get('positive_class', '')
        },
        'cross_validation': {
            'mean_weighted_f1': cv_results.get('mean_weighted_f1', 0.0),
            'std_weighted_f1': cv_results.get('std_weighted_f1', 0.0),
            'n_folds': cv_results.get('n_folds', 0),
            'per_fold_scores': cv_results.get('per_fold_scores', [])
        }
    }

    return report


def _format_per_class_metrics(classification_metrics):
    """Format per-class metrics for the report.

    Rounds all values to 6 decimal places for consistent output.

    Args:
        classification_metrics: dict mapping class name to metric dict

    Returns:
        Dict with rounded values.
    """
    formatted = {}
    for cls, metrics in classification_metrics.items():
        formatted[cls] = {
            'precision': round(metrics['precision'], 6),
            'recall': round(metrics['recall'], 6),
            'f1': round(metrics['f1'], 6)
        }
    return formatted


def write_report(report, output_path):
    """Write the evaluation report to a JSON file.

    Args:
        report: complete report dictionary
        output_path: path to write the JSON output
    """
    with open(output_path, 'w') as f:
        json.dump(report, f, indent=2, sort_keys=False)


def validate_report_structure(report):
    """Validate that a report has all required sections.

    Args:
        report: report dictionary to validate

    Returns:
        Tuple of (is_valid, list of missing sections).
    """
    required_sections = [
        'evaluation_metadata',
        'classification_report',
        'roc_auc',
        'calibration',
        'cross_validation'
    ]

    missing = []
    for section in required_sections:
        if section not in report:
            missing.append(section)

    return len(missing) == 0, missing


def format_summary_line(report):
    """Generate a one-line summary of evaluation results.

    Args:
        report: complete report dictionary

    Returns:
        Formatted summary string.
    """
    cr = report.get('classification_report', {})
    cv = report.get('cross_validation', {})
    roc = report.get('roc_auc', {})

    return (f"Accuracy={cr.get('accuracy', 0.0):.4f} | "
            f"Macro-F1={cr.get('macro_f1', 0.0):.4f} | "
            f"AUC={roc.get('macro_auc', 0.0):.4f} | "
            f"CV-F1={cv.get('mean_weighted_f1', 0.0):.4f}±{cv.get('std_weighted_f1', 0.0):.4f}")
