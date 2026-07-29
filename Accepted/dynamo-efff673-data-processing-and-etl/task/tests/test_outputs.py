"""
Verification tests for the event stream watermark pipeline.

Compares pipeline output against expected results on hidden stream configuration.
"""

import json
import os
import math

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_output():
    """Load the pipeline's output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-6):
    """Check approximate equality for floating point values."""
    if a == b:
        return True
    if a == 0 or b == 0:
        return abs(a - b) < 1e-9
    return abs(a - b) / max(abs(a), abs(b)) < rel_tol


def test_window_count():
    """Verify the correct number of windows are emitted."""
    output = load_output()
    expected = load_expected()
    assert len(output["window_results"]) == len(expected["window_results"]), \
        f"Expected {len(expected['window_results'])} windows, got {len(output['window_results'])}"


def test_window_keys():
    """Verify the correct windows are triggered and emitted."""
    output = load_output()
    expected = load_expected()
    output_keys = sorted([w["window_key"] for w in output["window_results"]])
    expected_keys = sorted([w["window_key"] for w in expected["window_results"]])
    assert output_keys == expected_keys, \
        f"Expected windows {expected_keys}, got {output_keys}"


def test_event_counts():
    """Verify per-window event counts match expected values."""
    output = load_output()
    expected = load_expected()
    for exp_w in expected["window_results"]:
        out_w = next(
            (w for w in output["window_results"] if w["window_key"] == exp_w["window_key"]),
            None
        )
        assert out_w is not None, f"Missing window {exp_w['window_key']}"
        assert out_w["event_count"] == exp_w["event_count"], \
            f"Window {exp_w['window_key']}: expected count {exp_w['event_count']}, got {out_w['event_count']}"


def test_sum_values():
    """Verify per-window sum values are computed correctly."""
    output = load_output()
    expected = load_expected()
    for exp_w in expected["window_results"]:
        out_w = next(
            (w for w in output["window_results"] if w["window_key"] == exp_w["window_key"]),
            None
        )
        assert out_w is not None, f"Missing window {exp_w['window_key']}"
        assert approx_equal(out_w["sum_value"], exp_w["sum_value"]), \
            f"Window {exp_w['window_key']}: expected sum {exp_w['sum_value']}, got {out_w['sum_value']}"


def test_combined_avg():
    """Verify combined average is computed as weighted mean across partitions."""
    output = load_output()
    expected = load_expected()
    for exp_w in expected["window_results"]:
        out_w = next(
            (w for w in output["window_results"] if w["window_key"] == exp_w["window_key"]),
            None
        )
        assert out_w is not None, f"Missing window {exp_w['window_key']}"
        assert approx_equal(out_w["combined_avg"], exp_w["combined_avg"]), \
            f"Window {exp_w['window_key']}: expected combined_avg {exp_w['combined_avg']}, got {out_w['combined_avg']}"


def test_combined_sum():
    """Verify combined sum values match expected output."""
    output = load_output()
    expected = load_expected()
    for exp_w in expected["window_results"]:
        out_w = next(
            (w for w in output["window_results"] if w["window_key"] == exp_w["window_key"]),
            None
        )
        assert out_w is not None, f"Missing window {exp_w['window_key']}"
        assert approx_equal(out_w["combined_sum"], exp_w["combined_sum"]), \
            f"Window {exp_w['window_key']}: expected combined_sum {exp_w['combined_sum']}, got {out_w['combined_sum']}"


def test_watermark_value():
    """Verify the global watermark is computed correctly."""
    output = load_output()
    expected = load_expected()
    assert approx_equal(
        output["watermark"]["global_watermark"],
        expected["watermark"]["global_watermark"]
    ), f"Expected watermark {expected['watermark']['global_watermark']}, got {output['watermark']['global_watermark']}"


def test_trigger_count():
    """Verify the correct number of windows are triggered."""
    output = load_output()
    expected = load_expected()
    assert output["trigger_summary"]["triggered_count"] == expected["trigger_summary"]["triggered_count"], \
        f"Expected {expected['trigger_summary']['triggered_count']} triggers, got {output['trigger_summary']['triggered_count']}"


def test_pending_count():
    """Verify pending window count after trigger evaluation."""
    output = load_output()
    expected = load_expected()
    assert output["trigger_summary"]["pending_count"] == expected["trigger_summary"]["pending_count"], \
        f"Expected {expected['trigger_summary']['pending_count']} pending, got {output['trigger_summary']['pending_count']}"


def test_late_event_handling():
    """Verify late event classification statistics."""
    output = load_output()
    expected = load_expected()
    for key in ["on_time_count", "late_allowed_count", "dropped_count"]:
        assert output["late_event_handling"][key] == expected["late_event_handling"][key], \
            f"late_event_handling.{key}: expected {expected['late_event_handling'][key]}, got {output['late_event_handling'][key]}"


def test_total_events_processed():
    """Verify total events processed in pipeline metadata."""
    output = load_output()
    expected = load_expected()
    assert output["pipeline_metadata"]["total_events_processed"] == \
        expected["pipeline_metadata"]["total_events_processed"], \
        f"Expected {expected['pipeline_metadata']['total_events_processed']} events processed, " \
        f"got {output['pipeline_metadata']['total_events_processed']}"


def test_output_statistics():
    """Verify output statistics across all emitted windows."""
    output = load_output()
    expected = load_expected()
    out_stats = output["watermark"]["output_statistics"]
    exp_stats = expected["watermark"]["output_statistics"]
    assert approx_equal(out_stats["total_sum"], exp_stats["total_sum"]), \
        f"total_sum: expected {exp_stats['total_sum']}, got {out_stats['total_sum']}"
    assert approx_equal(out_stats["overall_avg"], exp_stats["overall_avg"]), \
        f"overall_avg: expected {exp_stats['overall_avg']}, got {out_stats['overall_avg']}"
    assert out_stats["max_window_size"] == exp_stats["max_window_size"], \
        f"max_window_size: expected {exp_stats['max_window_size']}, got {out_stats['max_window_size']}"


def test_partition_lag():
    """Verify per-partition lag values are computed correctly."""
    output = load_output()
    expected = load_expected()
    out_lag = output["watermark"]["partition_lag"]
    exp_lag = expected["watermark"]["partition_lag"]
    assert set(out_lag.keys()) == set(exp_lag.keys()), \
        f"Partition lag keys differ: expected {set(exp_lag.keys())}, got {set(out_lag.keys())}"
    for pk in exp_lag:
        assert approx_equal(out_lag[pk], exp_lag[pk]), \
            f"partition_lag[{pk}]: expected {exp_lag[pk]}, got {out_lag[pk]}"


def test_partition_progress():
    """Verify per-partition watermark progress values."""
    output = load_output()
    expected = load_expected()
    out_prog = output["watermark"]["partition_progress"]
    exp_prog = expected["watermark"]["partition_progress"]
    assert set(out_prog.keys()) == set(exp_prog.keys()), \
        f"Partition progress keys differ: expected {set(exp_prog.keys())}, got {set(out_prog.keys())}"
    for pk in exp_prog:
        assert approx_equal(out_prog[pk], exp_prog[pk]), \
            f"partition_progress[{pk}]: expected {exp_prog[pk]}, got {out_prog[pk]}"
