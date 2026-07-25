"""
Calibration assessment module for model evaluation pipeline.

Computes Expected Calibration Error (ECE) and reliability diagram data
using binned probability calibration analysis.
"""


def compute_calibration_bins(probabilities, labels, positive_class, n_bins=10):
    """Compute calibration bins using equal-width strategy.

    Divides the [0, 1] probability range into equal-width bins and computes
    the mean predicted probability and actual positive rate in each bin.
    Empty bins are excluded from the result.

    Args:
        probabilities: list of probability scores for the positive class
        labels: list of true labels
        positive_class: the class considered positive
        n_bins: number of equal-width bins

    Returns:
        List of bin dicts with 'bin_lower', 'bin_upper', 'mean_predicted',
        'actual_positive_rate', and 'count'.
    """
    bin_width = 1.0 / n_bins
    bins = []

    for i in range(n_bins):
        bin_lower = i * bin_width
        bin_upper = (i + 1) * bin_width

        bin_probs = []
        bin_labels = []

        for prob, label in zip(probabilities, labels):
            if i < n_bins - 1:
                in_bin = bin_lower <= prob < bin_upper
            else:
                in_bin = bin_lower <= prob <= bin_upper

            if in_bin:
                bin_probs.append(prob)
                bin_labels.append(label)

        if len(bin_probs) > 0:
            mean_predicted = sum(bin_probs) / len(bin_probs)
            actual_positives = sum(1 for l in bin_labels if l == positive_class)
            actual_rate = actual_positives / len(bin_labels)

            bins.append({
                'bin_lower': round(bin_lower, 4),
                'bin_upper': round(bin_upper, 4),
                'mean_predicted': round(mean_predicted, 6),
                'actual_positive_rate': round(actual_rate, 6),
                'count': len(bin_probs)
            })

    return bins


def compute_ece(calibration_bins, total_samples):
    """Compute Expected Calibration Error from binned calibration data.

    ECE = sum over bins of (bin_count / total) * |mean_predicted - actual_rate|

    Args:
        calibration_bins: list of bin dicts from compute_calibration_bins
        total_samples: total number of samples across all bins

    Returns:
        Float ECE value.
    """
    if total_samples == 0:
        return 0.0

    ece = 0.0
    for bin_data in calibration_bins:
        weight = bin_data['count'] / total_samples
        gap = abs(bin_data['mean_predicted'] - bin_data['actual_positive_rate'])
        ece += weight * gap

    return round(ece, 6)


def compute_mce(calibration_bins):
    """Compute Maximum Calibration Error.

    MCE = max over bins of |mean_predicted - actual_rate|

    Args:
        calibration_bins: list of bin dicts from compute_calibration_bins

    Returns:
        Float MCE value.
    """
    if not calibration_bins:
        return 0.0

    max_gap = 0.0
    for bin_data in calibration_bins:
        gap = abs(bin_data['mean_predicted'] - bin_data['actual_positive_rate'])
        max_gap = max(max_gap, gap)

    return round(max_gap, 6)


def compute_calibration_metrics(predictions, labels, positive_class, n_bins=10):
    """Compute full calibration assessment for a binary classification.

    Assesses how well the predicted probabilities match actual outcomes.
    A well-calibrated model has predicted probabilities that match the
    empirical frequency of positives in each probability bin.

    Args:
        predictions: list of prediction dicts with 'probabilities' field
        labels: list of true labels corresponding to predictions
        positive_class: which class is considered positive
        n_bins: number of calibration bins

    Returns:
        Dict with 'ece', 'mce', 'bins', and 'n_samples' keys.
    """
    probabilities = []
    for pred in predictions:
        prob_dict = pred.get('probabilities', {})
        probabilities.append(prob_dict.get(positive_class, 0.0))

    bins = compute_calibration_bins(probabilities, labels, positive_class, n_bins)
    total_samples = len(probabilities)
    ece = compute_ece(bins, total_samples)
    mce = compute_mce(bins)

    return {
        'ece': ece,
        'mce': mce,
        'bins': bins,
        'n_samples': total_samples,
        'positive_class': positive_class
    }
