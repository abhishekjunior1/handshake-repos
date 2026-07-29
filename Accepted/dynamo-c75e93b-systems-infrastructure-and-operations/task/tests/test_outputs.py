"""
Verification tests for the metrics aggregation pipeline.
Compares pipeline output against expected values from the hidden test data.
"""

import json
import math
import pytest


EXPECTED_OUTPUT_FILE = "/tests/expected_output.json"
ACTUAL_OUTPUT_FILE = "/app/output.json"
REL_TOL = 1e-4


def load_json(filepath: str) -> dict:
    """Load a JSON file and return the parsed contents."""
    with open(filepath, "r") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected output from the test suite."""
    return load_json(EXPECTED_OUTPUT_FILE)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    return load_json(ACTUAL_OUTPUT_FILE)


def values_match(actual, expected, rel_tol=REL_TOL):
    """Check if two values match within relative tolerance."""
    if actual is None and expected is None:
        return True
    if actual is None or expected is None:
        return False
    if isinstance(actual, (int, float)) and isinstance(expected, (int, float)):
        if expected == 0:
            return abs(actual) < 1e-9
        return abs(actual - expected) / abs(expected) < rel_tol
    return actual == expected


class TestRateComputation:
    """Tests for counter rate computation correctness."""

    def test_rate_values_per_metric(self, actual_output, expected_output):
        """Verify per-second rate values are computed correctly for all counter metrics using time deltas between consecutive samples."""
        actual_rates = actual_output["rates"]
        expected_rates = expected_output["rates"]

        for name in expected_rates:
            assert name in actual_rates, f"Missing rate metric: {name}"
            expected_rate_list = expected_rates[name]["rates"]
            actual_rate_list = actual_rates[name]["rates"]
            assert len(actual_rate_list) == len(expected_rate_list), (
                f"Rate count mismatch for {name}: "
                f"got {len(actual_rate_list)}, expected {len(expected_rate_list)}"
            )
            for i, (act, exp) in enumerate(zip(actual_rate_list, expected_rate_list)):
                assert values_match(act["rate_per_sec"], exp["rate_per_sec"]), (
                    f"Rate mismatch for {name}[{i}]: "
                    f"got {act['rate_per_sec']}, expected {exp['rate_per_sec']}"
                )

    def test_mean_and_max_rates(self, actual_output, expected_output):
        """Verify mean and max rate aggregation values match expected per-second computations."""
        actual_rates = actual_output["rates"]
        expected_rates = expected_output["rates"]

        for name in expected_rates:
            assert name in actual_rates, f"Missing rate metric: {name}"
            assert values_match(
                actual_rates[name]["mean_rate"],
                expected_rates[name]["mean_rate"]
            ), (
                f"Mean rate mismatch for {name}: "
                f"got {actual_rates[name]['mean_rate']}, "
                f"expected {expected_rates[name]['mean_rate']}"
            )
            assert values_match(
                actual_rates[name]["max_rate"],
                expected_rates[name]["max_rate"]
            ), (
                f"Max rate mismatch for {name}: "
                f"got {actual_rates[name]['max_rate']}, "
                f"expected {expected_rates[name]['max_rate']}"
            )


class TestGaugeProcessing:
    """Tests for gauge metric processing correctness."""

    def test_gauge_statistics(self, actual_output, expected_output):
        """Verify gauge aggregation statistics (min, max, mean, count) match expected values including proper stale-marker handling."""
        actual_gauges = actual_output["gauges"]
        expected_gauges = expected_output["gauges"]

        for name in expected_gauges:
            assert name in actual_gauges, f"Missing gauge metric: {name}"
            for field in ["min", "max", "mean", "last", "count"]:
                assert values_match(
                    actual_gauges[name][field],
                    expected_gauges[name][field]
                ), (
                    f"Gauge {field} mismatch for {name}: "
                    f"got {actual_gauges[name][field]}, "
                    f"expected {expected_gauges[name][field]}"
                )

    def test_stale_marker_detection(self, actual_output, expected_output):
        """Verify stale-marker insertion count reflects correct Prometheus staleness convention (5-minute threshold)."""
        actual_gauges = actual_output["gauges"]
        expected_gauges = expected_output["gauges"]

        for name in expected_gauges:
            assert name in actual_gauges, f"Missing gauge metric: {name}"
            assert actual_gauges[name]["stale_markers_inserted"] == \
                   expected_gauges[name]["stale_markers_inserted"], (
                f"Stale marker count mismatch for {name}: "
                f"got {actual_gauges[name]['stale_markers_inserted']}, "
                f"expected {expected_gauges[name]['stale_markers_inserted']}"
            )


class TestHistogramProcessing:
    """Tests for histogram percentile computation correctness."""

    def test_histogram_percentiles(self, actual_output, expected_output):
        """Verify histogram percentiles (p50, p90, p95, p99) are computed correctly by merging bucket counts across sources before interpolation."""
        actual_hist = actual_output["histograms"]
        expected_hist = expected_output["histograms"]

        for name in expected_hist:
            assert name in actual_hist, f"Missing histogram metric: {name}"
            for pct in ["p50", "p90", "p95", "p99"]:
                assert values_match(
                    actual_hist[name][pct],
                    expected_hist[name][pct]
                ), (
                    f"Histogram {pct} mismatch for {name}: "
                    f"got {actual_hist[name][pct]}, "
                    f"expected {expected_hist[name][pct]}"
                )

    def test_histogram_total_observations(self, actual_output, expected_output):
        """Verify total observation count reflects the sum of all source contributions for each histogram metric."""
        actual_hist = actual_output["histograms"]
        expected_hist = expected_output["histograms"]

        for name in expected_hist:
            assert name in actual_hist, f"Missing histogram metric: {name}"
            assert values_match(
                actual_hist[name]["total_observations"],
                expected_hist[name]["total_observations"]
            ), (
                f"Total observations mismatch for {name}: "
                f"got {actual_hist[name]['total_observations']}, "
                f"expected {expected_hist[name]['total_observations']}"
            )


class TestRollups:
    """Tests for time-bucket rollup aggregation."""

    def test_rollup_structure(self, actual_output, expected_output):
        """Verify rollup output contains all expected metric names and correct bucket counts."""
        actual_rollups = actual_output["rollups"]
        expected_rollups = expected_output["rollups"]

        assert actual_rollups["rollup_interval_sec"] == expected_rollups["rollup_interval_sec"]

        for metric_type in ["counters", "gauges", "histograms"]:
            for name in expected_rollups[metric_type]:
                assert name in actual_rollups[metric_type], (
                    f"Missing rollup for {metric_type}/{name}"
                )
                assert actual_rollups[metric_type][name]["num_buckets"] == \
                       expected_rollups[metric_type][name]["num_buckets"], (
                    f"Bucket count mismatch for {metric_type}/{name}"
                )

    def test_counter_rollup_values(self, actual_output, expected_output):
        """Verify counter rollup rate values (mean_rate, max_rate) match expected per-second computations across time buckets."""
        actual_counters = actual_output["rollups"]["counters"]
        expected_counters = expected_output["rollups"]["counters"]

        for name in expected_counters:
            assert name in actual_counters, f"Missing counter rollup: {name}"
            actual_rollups = actual_counters[name]["rollups"]
            expected_rollups = expected_counters[name]["rollups"]
            for i, (act, exp) in enumerate(zip(actual_rollups, expected_rollups)):
                for field in ["mean_rate", "max_rate", "min_rate"]:
                    assert values_match(act[field], exp[field]), (
                        f"Counter rollup {field} mismatch for {name}[{i}]: "
                        f"got {act[field]}, expected {exp[field]}"
                    )

    def test_gauge_rollup_values(self, actual_output, expected_output):
        """Verify gauge rollup per-bucket values (min, max, mean, sum, last, count) match expected aggregation including partial-bucket extrapolation."""
        actual_gauges = actual_output["rollups"]["gauges"]
        expected_gauges = expected_output["rollups"]["gauges"]

        for name in expected_gauges:
            assert name in actual_gauges, f"Missing gauge rollup: {name}"
            actual_rollups = actual_gauges[name]["rollups"]
            expected_rollups = expected_gauges[name]["rollups"]
            assert len(actual_rollups) == len(expected_rollups), (
                f"Gauge rollup count mismatch for {name}: "
                f"got {len(actual_rollups)}, expected {len(expected_rollups)}"
            )
            for i, (act, exp) in enumerate(zip(actual_rollups, expected_rollups)):
                for field in ["min", "max", "mean", "sum", "last", "count"]:
                    assert values_match(act[field], exp[field]), (
                        f"Gauge rollup {field} mismatch for {name}[{i}]: "
                        f"got {act[field]}, expected {exp[field]}"
                    )

    def test_histogram_rollup_percentiles(self, actual_output, expected_output):
        """Verify histogram rollup percentiles match expected values from merged bucket computation."""
        actual_hist = actual_output["rollups"]["histograms"]
        expected_hist = expected_output["rollups"]["histograms"]

        for name in expected_hist:
            assert name in actual_hist, f"Missing histogram rollup: {name}"
            actual_rollups = actual_hist[name]["rollups"]
            expected_rollups = expected_hist[name]["rollups"]
            for i, (act, exp) in enumerate(zip(actual_rollups, expected_rollups)):
                for field in ["p50", "p90", "p95", "p99"]:
                    assert values_match(act[field], exp[field]), (
                        f"Histogram rollup {field} mismatch for {name}[{i}]: "
                        f"got {act[field]}, expected {exp[field]}"
                    )
