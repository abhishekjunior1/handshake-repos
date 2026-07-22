"""
Test suite for security event correlation pipeline output validation.

Compares the pipeline output against expected results to verify correctness
of deduplication, threat scoring, incident clustering, and report generation.
"""

import json
import pytest


EXPECTED_PATH = '/tests/expected_output.json'
ACTUAL_PATH = '/app/output.json'


@pytest.fixture
def expected_output():
    """Load the expected output from the reference file."""
    with open(EXPECTED_PATH, 'r') as f:
        return json.load(f)


@pytest.fixture
def actual_output():
    """Load the actual output produced by the pipeline."""
    with open(ACTUAL_PATH, 'r') as f:
        return json.load(f)


def get_entries_by_ip(report):
    """Helper to index threat entries by IP address."""
    entries = {}
    for entry in report.get('threat_entries', []):
        entries[entry['ip']] = entry
    return entries


class TestValidationSummary:
    """Tests for the validation summary section of the report."""

    def test_total_sources(self, expected_output, actual_output):
        """Verify the total number of unique source IPs matches expected."""
        expected = expected_output['validation_summary']['total_sources']
        actual = actual_output['validation_summary']['total_sources']
        assert actual == expected, (
            f"Total sources mismatch: expected {expected}, got {actual}"
        )

    def test_total_events(self, expected_output, actual_output):
        """Verify the total number of events after deduplication matches expected."""
        expected = expected_output['validation_summary']['total_events']
        actual = actual_output['validation_summary']['total_events']
        assert actual == expected, (
            f"Total events mismatch: expected {expected}, got {actual}"
        )

    def test_total_incidents(self, expected_output, actual_output):
        """Verify the total number of clustered incidents matches expected."""
        expected = expected_output['validation_summary']['total_incidents']
        actual = actual_output['validation_summary']['total_incidents']
        assert actual == expected, (
            f"Total incidents mismatch: expected {expected}, got {actual}"
        )


class TestThreatScores:
    """Tests for per-IP threat score accuracy."""

    def test_all_ips_present(self, expected_output, actual_output):
        """Verify all expected source IPs are present in the output."""
        expected_entries = get_entries_by_ip(expected_output)
        actual_entries = get_entries_by_ip(actual_output)
        expected_ips = set(expected_entries.keys())
        actual_ips = set(actual_entries.keys())
        assert actual_ips == expected_ips, (
            f"IP mismatch: missing {expected_ips - actual_ips}, "
            f"extra {actual_ips - expected_ips}"
        )

    def test_threat_scores(self, expected_output, actual_output):
        """Verify per-IP threat scores match within floating point tolerance."""
        expected_entries = get_entries_by_ip(expected_output)
        actual_entries = get_entries_by_ip(actual_output)

        for ip, expected_entry in expected_entries.items():
            actual_entry = actual_entries.get(ip)
            assert actual_entry is not None, f"Missing entry for IP: {ip}"

            expected_score = expected_entry['threat_score']
            actual_score = actual_entry['threat_score']
            assert abs(actual_score - expected_score) < 1e-6, (
                f"Threat score mismatch for {ip}: "
                f"expected {expected_score}, got {actual_score}"
            )


class TestEventCounts:
    """Tests for per-IP event count accuracy."""

    def test_event_counts(self, expected_output, actual_output):
        """Verify per-IP event counts match after deduplication."""
        expected_entries = get_entries_by_ip(expected_output)
        actual_entries = get_entries_by_ip(actual_output)

        for ip, expected_entry in expected_entries.items():
            actual_entry = actual_entries.get(ip)
            assert actual_entry is not None, f"Missing entry for IP: {ip}"

            expected_count = expected_entry['event_count']
            actual_count = actual_entry['event_count']
            assert actual_count == expected_count, (
                f"Event count mismatch for {ip}: "
                f"expected {expected_count}, got {actual_count}"
            )


class TestIncidents:
    """Tests for per-IP incident clustering accuracy."""

    def test_incident_counts(self, expected_output, actual_output):
        """Verify per-IP incident counts match expected clustering."""
        expected_entries = get_entries_by_ip(expected_output)
        actual_entries = get_entries_by_ip(actual_output)

        for ip, expected_entry in expected_entries.items():
            actual_entry = actual_entries.get(ip)
            assert actual_entry is not None, f"Missing entry for IP: {ip}"

            expected_count = expected_entry['incident_count']
            actual_count = actual_entry['incident_count']
            assert actual_count == expected_count, (
                f"Incident count mismatch for {ip}: "
                f"expected {expected_count}, got {actual_count}"
            )

    def test_incident_severities(self, expected_output, actual_output):
        """Verify per-IP incident severity values match within tolerance."""
        expected_entries = get_entries_by_ip(expected_output)
        actual_entries = get_entries_by_ip(actual_output)

        for ip, expected_entry in expected_entries.items():
            actual_entry = actual_entries.get(ip)
            assert actual_entry is not None, f"Missing entry for IP: {ip}"

            expected_incidents = sorted(
                expected_entry['incidents'],
                key=lambda x: x.get('start_time', 0)
            )
            actual_incidents = sorted(
                actual_entry['incidents'],
                key=lambda x: x.get('start_time', 0)
            )

            assert len(actual_incidents) == len(expected_incidents), (
                f"Incident count mismatch for {ip}: "
                f"expected {len(expected_incidents)}, got {len(actual_incidents)}"
            )

            for i, (exp_inc, act_inc) in enumerate(zip(expected_incidents, actual_incidents)):
                exp_sev = exp_inc['severity']
                act_sev = act_inc['severity']
                assert abs(act_sev - exp_sev) < 1e-6, (
                    f"Incident {i} severity mismatch for {ip}: "
                    f"expected {exp_sev}, got {act_sev}"
                )
