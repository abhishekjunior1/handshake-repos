"""
Stratified k-fold cross-validation module for model evaluation pipeline.

Implements stratified splitting and per-fold metric scoring with configurable
class-weighted aggregation.
"""


def create_stratified_folds(labels, classes, n_folds, random_seed):
    """Create stratified k-fold indices ensuring class proportions in each fold.

    Uses a deterministic assignment based on class-stratified round-robin
    with the random seed controlling the initial shuffle within each class.

    Args:
        labels: list of ground truth labels
        classes: list of class names
        n_folds: number of folds to create
        random_seed: seed for reproducible fold assignment

    Returns:
        List of n_folds lists, each containing sample indices for that fold.
    """
    class_indices = {cls: [] for cls in classes}
    for i, label in enumerate(labels):
        if label in class_indices:
            class_indices[label].append(i)

    for cls in classes:
        indices = class_indices[cls]
        _deterministic_shuffle(indices, random_seed)

    folds = [[] for _ in range(n_folds)]

    for cls in classes:
        indices = class_indices[cls]
        for i, idx in enumerate(indices):
            fold_assignment = i % n_folds
            folds[fold_assignment].append(idx)

    for fold in folds:
        fold.sort()

    return folds


def _deterministic_shuffle(items, seed):
    """Shuffle a list deterministically using a simple LCG-based approach.

    Uses a linear congruential generator for reproducibility without
    requiring external random libraries.
    """
    n = len(items)
    if n <= 1:
        return

    state = seed
    for i in range(n - 1, 0, -1):
        state = (state * 1103515245 + 12345) & 0x7fffffff
        j = state % (i + 1)
        items[i], items[j] = items[j], items[i]


def score_fold(fold_predictions, fold_labels, classes, sample_weights):
    """Score a single fold with class-weighted metrics.

    Computes per-class F1 scores within the fold and returns the
    weighted average using the provided sample_weights.

    The sample_weights should reflect the class distribution of the
    specific fold being scored, ensuring each fold's contribution
    accounts for its own composition.

    Args:
        fold_predictions: list of predicted labels for this fold
        fold_labels: list of true labels for this fold
        classes: ordered list of class names
        sample_weights: list of weights per class (must match classes order)

    Returns:
        Dict with 'weighted_f1', 'per_class_f1', and 'fold_size'.
    """
    per_class_f1 = {}

    for cls in classes:
        tp = sum(1 for p, t in zip(fold_predictions, fold_labels)
                 if p == cls and t == cls)
        fp = sum(1 for p, t in zip(fold_predictions, fold_labels)
                 if p == cls and t != cls)
        fn = sum(1 for p, t in zip(fold_predictions, fold_labels)
                 if p != cls and t == cls)

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)
               if (precision + recall) > 0 else 0.0)
        per_class_f1[cls] = f1

    f1_values = [per_class_f1[cls] for cls in classes]
    total_weight = sum(sample_weights)
    if total_weight > 0:
        weighted_f1 = sum(f * w for f, w in zip(f1_values, sample_weights)) / total_weight
    else:
        weighted_f1 = 0.0

    return {
        'weighted_f1': round(weighted_f1, 6),
        'per_class_f1': {cls: round(f1, 6) for cls, f1 in per_class_f1.items()},
        'fold_size': len(fold_labels)
    }


def aggregate_fold_scores(fold_results):
    """Aggregate scores across all folds.

    Computes mean and standard deviation of weighted F1 across folds.

    Args:
        fold_results: list of dicts from score_fold

    Returns:
        Dict with 'mean_weighted_f1', 'std_weighted_f1', 'n_folds',
        and 'per_fold_scores'.
    """
    scores = [r['weighted_f1'] for r in fold_results]
    n = len(scores)

    if n == 0:
        return {
            'mean_weighted_f1': 0.0,
            'std_weighted_f1': 0.0,
            'n_folds': 0,
            'per_fold_scores': []
        }

    mean_score = sum(scores) / n
    variance = sum((s - mean_score) ** 2 for s in scores) / n
    std_score = variance ** 0.5

    return {
        'mean_weighted_f1': round(mean_score, 6),
        'std_weighted_f1': round(std_score, 6),
        'n_folds': n,
        'per_fold_scores': [round(s, 6) for s in scores]
    }
