"""
Data loader module for model evaluation pipeline.

Handles loading evaluation configurations, predictions, and ground truth labels
from JSON configuration files. Supports both single-split and train/test split
evaluation modes.
"""

import json
import os
import sys


def load_config(config_path):
    """Load and validate the evaluation configuration file.

    The configuration specifies the evaluation mode, class definitions,
    predictions, labels, and cross-validation parameters.

    Returns a validated configuration dictionary.
    """
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, 'r') as f:
        config = json.load(f)

    required_keys = ['classes', 'predictions', 'labels', 'evaluation_mode']
    for key in required_keys:
        if key not in config:
            print(f"Error: Missing required key '{key}' in config", file=sys.stderr)
            sys.exit(1)

    return config


def extract_classes(config):
    """Extract the list of class names from configuration.

    Returns class names in the order they appear in the config.
    """
    classes = config['classes']
    if not isinstance(classes, list) or len(classes) < 2:
        print("Error: 'classes' must be a list with at least 2 elements", file=sys.stderr)
        sys.exit(1)
    return classes


def extract_predictions(config):
    """Extract prediction data from configuration.

    For single-split mode, returns predictions directly.
    For train-test mode, returns a dict with 'train' and 'test' keys.

    Each prediction entry contains:
      - 'predicted_class': the predicted label
      - 'probabilities': dict mapping class name to probability score
    """
    predictions = config['predictions']
    eval_mode = config['evaluation_mode']

    if eval_mode == 'single_split':
        return _validate_predictions(predictions)
    elif eval_mode == 'train_test':
        if 'train' not in predictions or 'test' not in predictions:
            print("Error: train_test mode requires 'train' and 'test' in predictions",
                  file=sys.stderr)
            sys.exit(1)
        return {
            'train': _validate_predictions(predictions['train']),
            'test': _validate_predictions(predictions['test'])
        }
    else:
        print(f"Error: Unknown evaluation_mode '{eval_mode}'", file=sys.stderr)
        sys.exit(1)


def extract_labels(config):
    """Extract ground truth labels from configuration.

    For single-split mode, returns labels directly.
    For train-test mode, returns a dict with 'train' and 'test' keys.
    """
    labels = config['labels']
    eval_mode = config['evaluation_mode']

    if eval_mode == 'single_split':
        return _validate_labels(labels)
    elif eval_mode == 'train_test':
        if 'train' not in labels or 'test' not in labels:
            print("Error: train_test mode requires 'train' and 'test' in labels",
                  file=sys.stderr)
            sys.exit(1)
        return {
            'train': _validate_labels(labels['train']),
            'test': _validate_labels(labels['test'])
        }
    else:
        print(f"Error: Unknown evaluation_mode '{eval_mode}'", file=sys.stderr)
        sys.exit(1)


def extract_cv_params(config):
    """Extract cross-validation parameters from configuration.

    Returns a dict with:
      - n_folds: number of folds for stratified k-fold
      - random_seed: seed for reproducible fold assignment
      - scoring_weights: how to weight class contributions in fold scoring
    """
    cv_params = config.get('cross_validation', {})
    return {
        'n_folds': cv_params.get('n_folds', 5),
        'random_seed': cv_params.get('random_seed', 42),
        'scoring_weights': cv_params.get('scoring_weights', 'class_distribution')
    }


def extract_calibration_params(config):
    """Extract calibration assessment parameters.

    Returns a dict with:
      - n_bins: number of bins for calibration curve
      - bin_strategy: 'equal_width' or 'equal_frequency'
    """
    cal_params = config.get('calibration', {})
    return {
        'n_bins': cal_params.get('n_bins', 10),
        'bin_strategy': cal_params.get('bin_strategy', 'equal_width')
    }


def get_evaluation_labels(config, labels_data):
    """Get the appropriate labels for evaluation based on mode.

    In single_split mode, the same labels are used for both training
    context and evaluation. In train_test mode, returns separate sets.

    Returns (train_labels, eval_labels) tuple.
    """
    eval_mode = config['evaluation_mode']

    if eval_mode == 'single_split':
        return labels_data, labels_data
    else:
        return labels_data['train'], labels_data['test']


def get_evaluation_predictions(config, predictions_data):
    """Get the appropriate predictions for evaluation based on mode.

    In single_split mode, the same predictions serve as both reference
    and evaluation target. In train_test mode, returns separate sets.

    Returns (train_predictions, eval_predictions) tuple.
    """
    eval_mode = config['evaluation_mode']

    if eval_mode == 'single_split':
        return predictions_data, predictions_data
    else:
        return predictions_data['train'], predictions_data['test']


def _validate_predictions(predictions):
    """Validate prediction entries have required fields."""
    if not isinstance(predictions, list) or len(predictions) == 0:
        print("Error: predictions must be a non-empty list", file=sys.stderr)
        sys.exit(1)

    for i, pred in enumerate(predictions):
        if 'predicted_class' not in pred:
            print(f"Error: prediction[{i}] missing 'predicted_class'", file=sys.stderr)
            sys.exit(1)
        if 'probabilities' not in pred:
            print(f"Error: prediction[{i}] missing 'probabilities'", file=sys.stderr)
            sys.exit(1)

    return predictions


def _validate_labels(labels):
    """Validate that labels is a non-empty list of strings."""
    if not isinstance(labels, list) or len(labels) == 0:
        print("Error: labels must be a non-empty list", file=sys.stderr)
        sys.exit(1)
    return labels
