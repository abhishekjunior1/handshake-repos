"""
Classification metrics module for model evaluation pipeline.

Computes standard classification metrics: precision, recall, F1, accuracy.
Supports per-class and macro-averaged computations with class prevalence ordering.
"""


def compute_confusion_matrix(predictions, labels, classes):
    """Compute a confusion matrix for multiclass classification.

    Args:
        predictions: list of predicted class labels
        labels: list of true class labels
        classes: ordered list of class names

    Returns:
        Dict mapping (true_class, pred_class) to count.
    """
    matrix = {}
    for true_cls in classes:
        for pred_cls in classes:
            matrix[(true_cls, pred_cls)] = 0

    for pred, true in zip(predictions, labels):
        if (true, pred) in matrix:
            matrix[(true, pred)] += 1

    return matrix


def compute_per_class_metrics(confusion_matrix, classes):
    """Compute precision, recall, and F1 for each class.

    Uses standard definitions:
      - precision = TP / (TP + FP)
      - recall = TP / (TP + FN)
      - F1 = 2 * precision * recall / (precision + recall)

    Args:
        confusion_matrix: dict from compute_confusion_matrix
        classes: ordered list of class names

    Returns:
        Dict mapping class_name to {'precision', 'recall', 'f1'} values.
    """
    metrics = {}

    for cls in classes:
        tp = confusion_matrix.get((cls, cls), 0)
        fp = sum(confusion_matrix.get((other, cls), 0)
                 for other in classes if other != cls)
        fn = sum(confusion_matrix.get((cls, other), 0)
                 for other in classes if other != cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
               if (precision + recall) > 0 else 0.0)

        metrics[cls] = {
            'precision': precision,
            'recall': recall,
            'f1': f1
        }

    return metrics


def compute_accuracy(predictions, labels):
    """Compute overall classification accuracy.

    Args:
        predictions: list of predicted class labels
        labels: list of true class labels

    Returns:
        Float accuracy score.
    """
    if len(predictions) == 0:
        return 0.0
    correct = sum(1 for p, t in zip(predictions, labels) if p == t)
    return correct / len(predictions)


def compute_macro_average(per_class_scores, class_order):
    """Compute macro-averaged metric from per-class scores.

    The scores must be provided in the specified class order for correct
    weighted averaging when class prevalences differ.

    Args:
        per_class_scores: list of scores ordered by class_order
        class_order: list of class names specifying the order of scores

    Returns:
        Float macro-averaged score (unweighted mean of per-class scores).
    """
    if len(per_class_scores) == 0:
        return 0.0
    return sum(per_class_scores) / len(per_class_scores)


def compute_weighted_average(per_class_scores, class_weights):
    """Compute weighted average of per-class scores.

    Args:
        per_class_scores: list of scores (must match class_weights order)
        class_weights: list of weights (typically class prevalences)

    Returns:
        Float weighted average score.
    """
    if len(per_class_scores) == 0:
        return 0.0
    total_weight = sum(class_weights)
    if total_weight == 0:
        return 0.0
    weighted_sum = sum(s * w for s, w in zip(per_class_scores, class_weights))
    return weighted_sum / total_weight


def get_class_prevalence_order(labels, classes):
    """Determine class ordering by prevalence (most frequent first).

    This is the canonical ordering used for macro-average computation
    in this pipeline — scores should be arranged in this order before
    passing to compute_macro_average.

    Args:
        labels: list of ground truth labels
        classes: list of all class names

    Returns:
        List of class names sorted by frequency (descending), with ties
        broken alphabetically.
    """
    counts = {}
    for cls in classes:
        counts[cls] = 0
    for label in labels:
        if label in counts:
            counts[label] += 1

    sorted_classes = sorted(classes, key=lambda c: (-counts[c], c))
    return sorted_classes


def compute_class_distribution(labels, classes):
    """Compute the distribution of classes in a label set.

    Args:
        labels: list of labels
        classes: ordered list of class names

    Returns:
        Dict mapping class_name to proportion (count / total).
    """
    total = len(labels)
    if total == 0:
        return {cls: 0.0 for cls in classes}

    counts = {cls: 0 for cls in classes}
    for label in labels:
        if label in counts:
            counts[label] += 1

    return {cls: counts[cls] / total for cls in classes}


def compute_class_weights(labels, classes):
    """Compute sample weights based on class distribution.

    Returns weights proportional to class frequency, normalized to sum to 1.
    Used for weighting fold-level metric computation.

    Args:
        labels: list of labels for weight computation
        classes: ordered list of class names

    Returns:
        List of weights in the order of classes parameter.
    """
    distribution = compute_class_distribution(labels, classes)
    weights = [distribution[cls] for cls in classes]
    return weights
