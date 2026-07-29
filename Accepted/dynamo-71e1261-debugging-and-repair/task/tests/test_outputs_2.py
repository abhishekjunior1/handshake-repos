"""
Test suite for secondary hidden configuration verification.

Ensures the pipeline generalizes correctly to different inputs —
validates all output fields match expected on a second dataset.
"""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PATH = os.path.join(TESTS_DIR, 'expected_output_2.json')
OUTPUT_PATH = '/app/output.json'


@pytest.fixture
def expected_output():
    """Load the expected output for secondary dataset."""
    with open(EXPECTED_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    with open(OUTPUT_PATH, 'r') as f:
        return json.load(f)


def test_secondary_output_exists():
    """Verify pipeline produces output for secondary input."""
    assert os.path.exists(OUTPUT_PATH)


def test_secondary_suite_name(actual_output, expected_output):
    """Verify suite name matches secondary expected."""
    assert actual_output['suite'] == expected_output['suite']


def test_secondary_analysis_summary(actual_output, expected_output):
    """Verify analysis summary for secondary dataset."""
    assert actual_output['analysis_summary'] == expected_output['analysis_summary']


def test_secondary_classification_count(actual_output, expected_output):
    """Verify correct number of classifications on secondary dataset."""
    assert len(actual_output['classifications']) == len(expected_output['classifications'])


def test_secondary_classifications(actual_output, expected_output):
    """Verify classification categories match on secondary dataset."""
    out_cats = {c['test_id']: c['category'] for c in actual_output['classifications']}
    exp_cats = {c['test_id']: c['category'] for c in expected_output['classifications']}
    assert out_cats == exp_cats


def test_secondary_confidence(actual_output, expected_output):
    """Verify confidence scores on secondary dataset."""
    out_map = {c['test_id']: c['confidence'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['confidence'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.01


def test_secondary_failure_rates(actual_output, expected_output):
    """Verify failure rates on secondary dataset."""
    out_map = {c['test_id']: c['metrics']['failure_rate'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['metrics']['failure_rate'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.001


def test_secondary_recent_failure_rates(actual_output, expected_output):
    """Verify recent failure rates on secondary dataset."""
    out_map = {c['test_id']: c['metrics']['recent_failure_rate'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['metrics']['recent_failure_rate'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.001


def test_secondary_flip_rates(actual_output, expected_output):
    """Verify flip rates on secondary dataset."""
    out_map = {c['test_id']: c['metrics']['flip_rate'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['metrics']['flip_rate'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.001


def test_secondary_correlation_matrix(actual_output, expected_output):
    """Verify correlation matrix on secondary dataset."""
    assert actual_output['correlation_matrix'] == expected_output['correlation_matrix']


def test_secondary_timing_baselines(actual_output, expected_output):
    """Verify timing baselines on secondary dataset."""
    assert actual_output['timing_baselines'] == expected_output['timing_baselines']


def test_secondary_overall_health(actual_output, expected_output):
    """Verify overall health percentages on secondary dataset."""
    for key in expected_output['overall_health']:
        out_val = actual_output['overall_health'].get(key, -1)
        exp_val = expected_output['overall_health'][key]
        assert abs(out_val - exp_val) < 0.001


def test_secondary_windowed_rates(actual_output, expected_output):
    """Verify windowed rates on secondary dataset."""
    out_map = {c['test_id']: c['windowed_rates'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['windowed_rates'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert out_map.get(tid) == exp_map[tid]


def test_secondary_trends(actual_output, expected_output):
    """Verify trends on secondary dataset."""
    out_map = {c['test_id']: c['trend'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['trend'] for c in expected_output['classifications']}
    assert out_map == exp_map


def test_secondary_correlated_tests(actual_output, expected_output):
    """Verify correlated tests on secondary dataset."""
    out_map = {c['test_id']: sorted(c.get('correlated_tests', [])) for c in actual_output['classifications']}
    exp_map = {c['test_id']: sorted(c.get('correlated_tests', [])) for c in expected_output['classifications']}
    assert out_map == exp_map
