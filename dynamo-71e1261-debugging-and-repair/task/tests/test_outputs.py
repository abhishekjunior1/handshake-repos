"""
Test suite for flaky test diagnosis pipeline output verification.

Compares the pipeline output against expected results for the hidden test
configuration that exercises correlation analysis and classification bugs.
"""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
EXPECTED_PATH = os.path.join(TESTS_DIR, 'expected_output.json')
OUTPUT_PATH = '/app/output.json'


@pytest.fixture
def expected_output():
    """Load the expected output JSON."""
    with open(EXPECTED_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output JSON."""
    with open(OUTPUT_PATH, 'r') as f:
        return json.load(f)


def test_output_exists():
    """Verify pipeline produces output file."""
    assert os.path.exists(OUTPUT_PATH), f"No output at {OUTPUT_PATH}"


def test_required_keys(actual_output):
    """Verify all required top-level keys present in output."""
    for key in ['suite', 'analysis_summary', 'classifications',
                'correlation_matrix', 'timing_baselines', 'overall_health']:
        assert key in actual_output, f"Missing key: {key}"


def test_suite_name(actual_output, expected_output):
    """Verify suite name matches expected."""
    assert actual_output['suite'] == expected_output['suite']


def test_analysis_summary(actual_output, expected_output):
    """Verify analysis summary counts match expected."""
    assert actual_output['analysis_summary'] == expected_output['analysis_summary']


def test_classification_count(actual_output, expected_output):
    """Verify correct number of test classifications produced."""
    assert len(actual_output['classifications']) == len(expected_output['classifications'])


def test_classification_categories(actual_output, expected_output):
    """Verify each test receives the correct category assignment."""
    out_map = {c['test_id']: c['category'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['category'] for c in expected_output['classifications']}
    assert out_map == exp_map, f"Category mismatch:\nExpected: {exp_map}\nGot: {out_map}"


def test_classification_confidence(actual_output, expected_output):
    """Verify confidence scores are within tolerance."""
    out_map = {c['test_id']: c['confidence'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['confidence'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert tid in out_map, f"Missing test: {tid}"
        assert abs(out_map[tid] - exp_map[tid]) < 0.01, (
            f"{tid}: confidence {out_map[tid]} != expected {exp_map[tid]}"
        )


def test_failure_rates(actual_output, expected_output):
    """Verify per-test failure rate metrics match expected."""
    out_map = {c['test_id']: c['metrics']['failure_rate'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['metrics']['failure_rate'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.001, (
            f"{tid}: failure_rate {out_map.get(tid)} != {exp_map[tid]}"
        )


def test_recent_failure_rates(actual_output, expected_output):
    """Verify recent failure rate metrics use correct windowed computation."""
    out_map = {c['test_id']: c['metrics']['recent_failure_rate'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['metrics']['recent_failure_rate'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.001, (
            f"{tid}: recent_failure_rate {out_map.get(tid)} != {exp_map[tid]}"
        )


def test_flip_rates(actual_output, expected_output):
    """Verify flip rate computation for state transition detection."""
    out_map = {c['test_id']: c['metrics']['flip_rate'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['metrics']['flip_rate'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert abs(out_map.get(tid, -1) - exp_map[tid]) < 0.001, (
            f"{tid}: flip_rate {out_map.get(tid)} != {exp_map[tid]}"
        )


def test_correlation_matrix(actual_output, expected_output):
    """Verify pairwise correlation values match expected analysis."""
    assert actual_output['correlation_matrix'] == expected_output['correlation_matrix']


def test_timing_baselines(actual_output, expected_output):
    """Verify per-module timing baselines are computed correctly."""
    assert actual_output['timing_baselines'] == expected_output['timing_baselines']


def test_overall_health(actual_output, expected_output):
    """Verify overall health percentage breakdown matches expected."""
    for key in expected_output['overall_health']:
        out_val = actual_output['overall_health'].get(key, -1)
        exp_val = expected_output['overall_health'][key]
        assert abs(out_val - exp_val) < 0.001, (
            f"overall_health.{key}: {out_val} != {exp_val}"
        )


def test_windowed_rates(actual_output, expected_output):
    """Verify windowed failure rate sequences for trend analysis."""
    out_map = {c['test_id']: c['windowed_rates'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['windowed_rates'] for c in expected_output['classifications']}
    for tid in exp_map:
        assert out_map.get(tid) == exp_map[tid], (
            f"{tid}: windowed_rates {out_map.get(tid)} != {exp_map[tid]}"
        )


def test_trends(actual_output, expected_output):
    """Verify failure trend classification for each test."""
    out_map = {c['test_id']: c['trend'] for c in actual_output['classifications']}
    exp_map = {c['test_id']: c['trend'] for c in expected_output['classifications']}
    assert out_map == exp_map


def test_correlated_tests(actual_output, expected_output):
    """Verify correlated test pairs are identified correctly."""
    out_map = {c['test_id']: sorted(c.get('correlated_tests', [])) for c in actual_output['classifications']}
    exp_map = {c['test_id']: sorted(c.get('correlated_tests', [])) for c in expected_output['classifications']}
    assert out_map == exp_map
