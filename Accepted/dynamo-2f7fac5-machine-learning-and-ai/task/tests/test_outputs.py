"""
Tests for the model evaluation pipeline.

Verifies that the pipeline produces correct output when run on hidden
evaluation data with separate train/test splits and imbalanced classes.
"""

import json
import os
import subprocess
import math

EXPECTED_OUTPUT_PATH = "/tests/expected_output.json"
ACTUAL_OUTPUT_PATH = "/app/output.json"
HIDDEN_CONFIG_PATH = "/tests/eval_config_hidden.json"
PIPELINE_PATH = "/app/pipeline.py"
VISIBLE_CONFIG_PATH = "/app/eval_config.json"


def _run_pipeline_on_hidden_data():
    """Run the pipeline on hidden test data and return the output."""
    # Copy hidden config as the pipeline input
    import shutil
    shutil.copy(HIDDEN_CONFIG_PATH, VISIBLE_CONFIG_PATH)

    result = subprocess.run(
        ["python3", PIPELINE_PATH, VISIBLE_CONFIG_PATH, ACTUAL_OUTPUT_PATH],
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0, f"Pipeline failed: {result.stderr}"

    with open(ACTUAL_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def _load_expected():
    """Load expected output."""
    with open(EXPECTED_OUTPUT_PATH, 'r') as f:
        return json.load(f)


def _approx_equal(a, b, rel_tol=1e-4):
    """Check approximate equality with relative tolerance."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if a == 0 and b == 0:
            return True
        return abs(a - b) <= rel_tol * max(abs(a), abs(b))
    return a == b


class TestPipelineOutput:
    """Test suite for model evaluation pipeline correctness."""

    def setup_method(self):
        """Set up test fixtures by running the pipeline on hidden data."""
        self.actual = _run_pipeline_on_hidden_data()
        self.expected = _load_expected()

    def test_output_file_exists(self):
        """Verify that the pipeline produces an output.json file."""
        assert os.path.exists(ACTUAL_OUTPUT_PATH), \
            f"Expected output file at {ACTUAL_OUTPUT_PATH}"

    def test_output_is_valid_json(self):
        """Verify that the output is valid JSON with expected top-level structure."""
        required_keys = [
            'evaluation_metadata', 'classification_report',
            'roc_auc', 'calibration', 'cross_validation'
        ]
        for key in required_keys:
            assert key in self.actual, f"Missing required section: {key}"

    def test_evaluation_metadata(self):
        """Verify evaluation metadata matches expected configuration."""
        actual_meta = self.actual['evaluation_metadata']
        expected_meta = self.expected['evaluation_metadata']
        assert actual_meta['evaluation_mode'] == expected_meta['evaluation_mode']
        assert actual_meta['n_classes'] == expected_meta['n_classes']
        assert actual_meta['n_samples_evaluated'] == expected_meta['n_samples_evaluated']

    def test_accuracy(self):
        """Verify overall classification accuracy is computed correctly."""
        actual_acc = self.actual['classification_report']['accuracy']
        expected_acc = self.expected['classification_report']['accuracy']
        assert _approx_equal(actual_acc, expected_acc), \
            f"Accuracy mismatch: got {actual_acc}, expected {expected_acc}"

    def test_macro_f1(self):
        """Verify macro-averaged F1 score is computed correctly."""
        actual_f1 = self.actual['classification_report']['macro_f1']
        expected_f1 = self.expected['classification_report']['macro_f1']
        assert _approx_equal(actual_f1, expected_f1), \
            f"Macro F1 mismatch: got {actual_f1}, expected {expected_f1}"

    def test_weighted_f1(self):
        """Verify weighted-averaged F1 score accounts for class prevalence correctly."""
        actual_wf1 = self.actual['classification_report']['weighted_f1']
        expected_wf1 = self.expected['classification_report']['weighted_f1']
        assert _approx_equal(actual_wf1, expected_wf1), \
            f"Weighted F1 mismatch: got {actual_wf1}, expected {expected_wf1}"

    def test_per_class_precision(self):
        """Verify per-class precision values are computed correctly."""
        actual_pc = self.actual['classification_report']['per_class']
        expected_pc = self.expected['classification_report']['per_class']
        for cls in expected_pc:
            assert cls in actual_pc, f"Missing class: {cls}"
            assert _approx_equal(actual_pc[cls]['precision'], expected_pc[cls]['precision']), \
                f"Precision mismatch for {cls}: got {actual_pc[cls]['precision']}, expected {expected_pc[cls]['precision']}"

    def test_per_class_recall(self):
        """Verify per-class recall values are computed correctly."""
        actual_pc = self.actual['classification_report']['per_class']
        expected_pc = self.expected['classification_report']['per_class']
        for cls in expected_pc:
            assert _approx_equal(actual_pc[cls]['recall'], expected_pc[cls]['recall']), \
                f"Recall mismatch for {cls}: got {actual_pc[cls]['recall']}, expected {expected_pc[cls]['recall']}"

    def test_per_class_f1(self):
        """Verify per-class F1 scores are computed correctly."""
        actual_pc = self.actual['classification_report']['per_class']
        expected_pc = self.expected['classification_report']['per_class']
        for cls in expected_pc:
            assert _approx_equal(actual_pc[cls]['f1'], expected_pc[cls]['f1']), \
                f"F1 mismatch for {cls}: got {actual_pc[cls]['f1']}, expected {expected_pc[cls]['f1']}"

    def test_roc_auc_macro(self):
        """Verify macro-averaged ROC-AUC is computed correctly on probability scores."""
        actual_auc = self.actual['roc_auc']['macro_auc']
        expected_auc = self.expected['roc_auc']['macro_auc']
        assert _approx_equal(actual_auc, expected_auc), \
            f"Macro AUC mismatch: got {actual_auc}, expected {expected_auc}"

    def test_roc_auc_per_class(self):
        """Verify per-class ROC-AUC values are computed correctly."""
        actual_auc = self.actual['roc_auc']['per_class_auc']
        expected_auc = self.expected['roc_auc']['per_class_auc']
        for cls in expected_auc:
            assert cls in actual_auc, f"Missing AUC for class: {cls}"
            assert _approx_equal(actual_auc[cls], expected_auc[cls]), \
                f"AUC mismatch for {cls}: got {actual_auc[cls]}, expected {expected_auc[cls]}"

    def test_calibration_ece(self):
        """Verify Expected Calibration Error is computed with correct labels."""
        actual_ece = self.actual['calibration']['ece']
        expected_ece = self.expected['calibration']['ece']
        assert _approx_equal(actual_ece, expected_ece), \
            f"ECE mismatch: got {actual_ece}, expected {expected_ece}"

    def test_calibration_mce(self):
        """Verify Maximum Calibration Error is computed with correct labels."""
        actual_mce = self.actual['calibration']['mce']
        expected_mce = self.expected['calibration']['mce']
        assert _approx_equal(actual_mce, expected_mce), \
            f"MCE mismatch: got {actual_mce}, expected {expected_mce}"

    def test_cv_mean_weighted_f1(self):
        """Verify cross-validation mean weighted F1 uses per-fold class weights."""
        actual_cv = self.actual['cross_validation']['mean_weighted_f1']
        expected_cv = self.expected['cross_validation']['mean_weighted_f1']
        assert _approx_equal(actual_cv, expected_cv), \
            f"CV mean F1 mismatch: got {actual_cv}, expected {expected_cv}"

    def test_cv_std_weighted_f1(self):
        """Verify cross-validation standard deviation of weighted F1 scores."""
        actual_std = self.actual['cross_validation']['std_weighted_f1']
        expected_std = self.expected['cross_validation']['std_weighted_f1']
        assert _approx_equal(actual_std, expected_std), \
            f"CV std mismatch: got {actual_std}, expected {expected_std}"

    def test_cv_per_fold_scores(self):
        """Verify individual fold scores reflect per-fold class weighting."""
        actual_scores = self.actual['cross_validation']['per_fold_scores']
        expected_scores = self.expected['cross_validation']['per_fold_scores']
        assert len(actual_scores) == len(expected_scores), \
            f"Fold count mismatch: got {len(actual_scores)}, expected {len(expected_scores)}"
        for i, (a, e) in enumerate(zip(actual_scores, expected_scores)):
            assert _approx_equal(a, e), \
                f"Fold {i} score mismatch: got {a}, expected {e}"

    def test_cv_n_folds(self):
        """Verify the correct number of cross-validation folds were computed."""
        assert self.actual['cross_validation']['n_folds'] == \
            self.expected['cross_validation']['n_folds']
