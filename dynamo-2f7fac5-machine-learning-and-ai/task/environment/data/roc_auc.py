"""
ROC-AUC computation module for model evaluation pipeline.

Computes Receiver Operating Characteristic Area Under Curve for binary
and multiclass classification using the one-vs-rest approach.
"""


def compute_roc_curve(probabilities, labels, positive_class):
    """Compute ROC curve points for a single class (one-vs-rest).

    Uses probability scores directly to generate threshold-based
    true positive rate (TPR) and false positive rate (FPR) at
    multiple operating points.

    Args:
        probabilities: list of probability scores for the positive class
        labels: list of true labels
        positive_class: the class name considered positive

    Returns:
        Tuple of (fpr_list, tpr_list, thresholds) sorted by threshold.
    """
    scored_items = []
    for prob, label in zip(probabilities, labels):
        is_positive = 1 if label == positive_class else 0
        scored_items.append((prob, is_positive))

    scored_items.sort(key=lambda x: -x[0])

    total_positives = sum(1 for _, is_pos in scored_items if is_pos == 1)
    total_negatives = len(scored_items) - total_positives

    if total_positives == 0 or total_negatives == 0:
        return [0.0, 1.0], [0.0, 1.0], [1.0, 0.0]

    fpr_list = [0.0]
    tpr_list = [0.0]
    thresholds = [scored_items[0][0] + 1.0]

    tp_count = 0
    fp_count = 0

    for i, (score, is_pos) in enumerate(scored_items):
        if is_pos == 1:
            tp_count += 1
        else:
            fp_count += 1

        if i < len(scored_items) - 1 and scored_items[i + 1][0] == score:
            continue

        tpr = tp_count / total_positives
        fpr = fp_count / total_negatives
        fpr_list.append(fpr)
        tpr_list.append(tpr)
        thresholds.append(score)

    return fpr_list, tpr_list, thresholds


def compute_auc(fpr_list, tpr_list):
    """Compute Area Under Curve using the trapezoidal rule.

    Args:
        fpr_list: list of false positive rates (x-axis)
        tpr_list: list of true positive rates (y-axis)

    Returns:
        Float AUC value between 0 and 1.
    """
    auc = 0.0
    for i in range(1, len(fpr_list)):
        width = fpr_list[i] - fpr_list[i - 1]
        height = (tpr_list[i] + tpr_list[i - 1]) / 2.0
        auc += width * height
    return auc


def compute_multiclass_roc_auc(predictions, labels, classes):
    """Compute multiclass ROC-AUC using one-vs-rest macro averaging.

    For each class, computes ROC-AUC treating that class as positive
    and all others as negative. The final score is the macro average.

    Args:
        predictions: list of prediction dicts with 'probabilities' field
        labels: list of true class labels
        classes: list of class names

    Returns:
        Dict with 'per_class_auc' and 'macro_auc' keys.
    """
    per_class_auc = {}

    for cls in classes:
        probs = []
        for pred in predictions:
            prob_dict = pred['probabilities']
            probs.append(prob_dict.get(cls, 0.0))

        fpr, tpr, _ = compute_roc_curve(probs, labels, cls)
        auc = compute_auc(fpr, tpr)
        per_class_auc[cls] = round(auc, 6)

    macro_auc = sum(per_class_auc.values()) / len(per_class_auc) if per_class_auc else 0.0

    return {
        'per_class_auc': per_class_auc,
        'macro_auc': round(macro_auc, 6)
    }


def extract_class_probabilities(predictions, target_class):
    """Extract probability scores for a specific class from predictions.

    Args:
        predictions: list of prediction dicts
        target_class: class name to extract probabilities for

    Returns:
        List of probability scores for the target class.
    """
    probs = []
    for pred in predictions:
        prob_dict = pred.get('probabilities', {})
        probs.append(prob_dict.get(target_class, 0.0))
    return probs
