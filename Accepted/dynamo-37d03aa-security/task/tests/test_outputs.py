"""Test suite for CIS compliance scanner pipeline output verification.

Validates all fields in the pipeline output against expected values from
the compliance evaluation of the hidden configuration.
"""

import json
import math
import pytest


@pytest.fixture
def actual_output():
    """Load the pipeline output produced by the agent's code."""
    with open("/app/output.json", "r") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected reference output for verification."""
    with open("/tests/expected_output.json", "r") as f:
        return json.load(f)


class TestSummary:
    """Tests for the summary section of the compliance report."""

    def test_overall_compliance_score(self, actual_output, expected_output):
        """Verify the overall CVSS-weighted compliance score is correct."""
        actual = actual_output["summary"]["overall_compliance_score"]
        expected = expected_output["summary"]["overall_compliance_score"]
        assert math.isclose(actual, expected, rel_tol=1e-4), (
            f"Overall compliance score {actual} != expected {expected}"
        )

    def test_compliance_status(self, actual_output, expected_output):
        """Verify the compliance status determination (PASS/FAIL)."""
        actual = actual_output["summary"]["compliance_status"]
        expected = expected_output["summary"]["compliance_status"]
        assert actual == expected, (
            f"Compliance status '{actual}' != expected '{expected}'"
        )

    def test_total_controls_evaluated(self, actual_output, expected_output):
        """Verify total number of controls evaluated (scored + informational)."""
        actual = actual_output["summary"]["total_controls_evaluated"]
        expected = expected_output["summary"]["total_controls_evaluated"]
        assert actual == expected, (
            f"Total controls evaluated {actual} != expected {expected}"
        )

    def test_scored_controls_count(self, actual_output, expected_output):
        """Verify the count of scored controls (excludes informational)."""
        actual = actual_output["summary"]["scored_controls"]
        expected = expected_output["summary"]["scored_controls"]
        assert actual == expected, (
            f"Scored controls {actual} != expected {expected}"
        )

    def test_informational_controls_count(self, actual_output, expected_output):
        """Verify the count of informational controls excluded from scoring."""
        actual = actual_output["summary"]["informational_controls"]
        expected = expected_output["summary"]["informational_controls"]
        assert actual == expected, (
            f"Informational controls {actual} != expected {expected}"
        )

    def test_controls_passed(self, actual_output, expected_output):
        """Verify the count of controls with passing status."""
        actual = actual_output["summary"]["controls_passed"]
        expected = expected_output["summary"]["controls_passed"]
        assert actual == expected, (
            f"Controls passed {actual} != expected {expected}"
        )

    def test_controls_failed(self, actual_output, expected_output):
        """Verify the count of controls with failing status."""
        actual = actual_output["summary"]["controls_failed"]
        expected = expected_output["summary"]["controls_failed"]
        assert actual == expected, (
            f"Controls failed {actual} != expected {expected}"
        )

    def test_controls_waived(self, actual_output, expected_output):
        """Verify the count of controls with waived status (exception applied)."""
        actual = actual_output["summary"]["controls_waived"]
        expected = expected_output["summary"]["controls_waived"]
        assert actual == expected, (
            f"Controls waived {actual} != expected {expected}"
        )

    def test_pass_rate(self, actual_output, expected_output):
        """Verify the pass rate (passed + waived) / scored_controls."""
        actual = actual_output["summary"]["pass_rate"]
        expected = expected_output["summary"]["pass_rate"]
        assert math.isclose(actual, expected, rel_tol=1e-4), (
            f"Pass rate {actual} != expected {expected}"
        )


class TestSectionBreakdown:
    """Tests for the per-section breakdown of the compliance report."""

    def test_section_count(self, actual_output, expected_output):
        """Verify the correct number of sections in the breakdown."""
        actual = len(actual_output["section_breakdown"])
        expected = len(expected_output["section_breakdown"])
        assert actual == expected, (
            f"Section count {actual} != expected {expected}"
        )

    def test_section_ids(self, actual_output, expected_output):
        """Verify all expected section IDs are present in the breakdown."""
        actual_ids = {s["section_id"] for s in actual_output["section_breakdown"]}
        expected_ids = {s["section_id"] for s in expected_output["section_breakdown"]}
        assert actual_ids == expected_ids, (
            f"Section IDs {actual_ids} != expected {expected_ids}"
        )

    def test_section_scores(self, actual_output, expected_output):
        """Verify per-section compliance scores match expected values."""
        actual_sections = {s["section_id"]: s for s in actual_output["section_breakdown"]}
        expected_sections = {s["section_id"]: s for s in expected_output["section_breakdown"]}

        for section_id, expected_section in expected_sections.items():
            assert section_id in actual_sections, (
                f"Missing section '{section_id}' in output"
            )
            actual_score = actual_sections[section_id]["compliance_score"]
            expected_score = expected_section["compliance_score"]
            assert math.isclose(actual_score, expected_score, rel_tol=1e-4), (
                f"Section '{section_id}' score {actual_score} != expected {expected_score}"
            )

    def test_section_control_counts(self, actual_output, expected_output):
        """Verify per-section control counts (total, passed, failed, waived)."""
        actual_sections = {s["section_id"]: s for s in actual_output["section_breakdown"]}
        expected_sections = {s["section_id"]: s for s in expected_output["section_breakdown"]}

        for section_id, expected_section in expected_sections.items():
            actual_section = actual_sections[section_id]
            assert actual_section["total_controls"] == expected_section["total_controls"], (
                f"Section '{section_id}' total_controls mismatch"
            )
            assert actual_section["passed"] == expected_section["passed"], (
                f"Section '{section_id}' passed count mismatch"
            )
            assert actual_section["failed"] == expected_section["failed"], (
                f"Section '{section_id}' failed count mismatch"
            )
            assert actual_section["waived"] == expected_section["waived"], (
                f"Section '{section_id}' waived count mismatch"
            )


class TestControlDetails:
    """Tests for individual control evaluation results."""

    def test_control_details_count(self, actual_output, expected_output):
        """Verify the total number of control detail entries."""
        actual = len(actual_output["control_details"])
        expected = len(expected_output["control_details"])
        assert actual == expected, (
            f"Control details count {actual} != expected {expected}"
        )

    def test_control_statuses(self, actual_output, expected_output):
        """Verify each control-resource pair has the correct status."""
        actual_details = {
            (d["control_id"], d["resource_id"]): d
            for d in actual_output["control_details"]
        }
        expected_details = {
            (d["control_id"], d["resource_id"]): d
            for d in expected_output["control_details"]
        }

        for key, expected_detail in expected_details.items():
            assert key in actual_details, (
                f"Missing control detail for {key}"
            )
            actual_status = actual_details[key]["status"]
            expected_status = expected_detail["status"]
            assert actual_status == expected_status, (
                f"Control {key} status '{actual_status}' != expected '{expected_status}'"
            )

    def test_waived_controls_have_waiver_info(self, actual_output, expected_output):
        """Verify waived controls include waiver_id and reason."""
        expected_waived = [
            d for d in expected_output["control_details"]
            if d["status"] == "waived"
        ]
        actual_details = {
            (d["control_id"], d["resource_id"]): d
            for d in actual_output["control_details"]
        }

        for expected_detail in expected_waived:
            key = (expected_detail["control_id"], expected_detail["resource_id"])
            actual_detail = actual_details.get(key, {})
            assert actual_detail.get("status") == "waived", (
                f"Control {key} should be waived"
            )
            assert actual_detail.get("waiver_id") == expected_detail["waiver_id"], (
                f"Control {key} waiver_id mismatch"
            )

    def test_control_severity_values(self, actual_output, expected_output):
        """Verify severity values reflect inheritance resolution."""
        actual_details = {
            (d["control_id"], d["resource_id"]): d
            for d in actual_output["control_details"]
        }
        expected_details = {
            (d["control_id"], d["resource_id"]): d
            for d in expected_output["control_details"]
        }

        for key, expected_detail in expected_details.items():
            if key in actual_details:
                assert actual_details[key]["severity"] == expected_detail["severity"], (
                    f"Control {key} severity mismatch"
                )

    def test_control_full_paths(self, actual_output, expected_output):
        """Verify hierarchical full path for each control evaluation."""
        actual_details = {
            (d["control_id"], d["resource_id"]): d
            for d in actual_output["control_details"]
        }
        expected_details = {
            (d["control_id"], d["resource_id"]): d
            for d in expected_output["control_details"]
        }

        for key, expected_detail in expected_details.items():
            if key in actual_details:
                assert actual_details[key]["full_path"] == expected_detail["full_path"], (
                    f"Control {key} full_path mismatch: "
                    f"'{actual_details[key]['full_path']}' != '{expected_detail['full_path']}'"
                )


class TestWaiverSummary:
    """Tests for waiver application summary statistics."""

    def test_total_waivers_applied(self, actual_output, expected_output):
        """Verify total count of waivers that were matched and applied."""
        actual = actual_output["waiver_summary"]["total_waivers_applied"]
        expected = expected_output["waiver_summary"]["total_waivers_applied"]
        assert actual == expected, (
            f"Total waivers applied {actual} != expected {expected}"
        )

    def test_waivers_by_severity(self, actual_output, expected_output):
        """Verify waiver counts broken down by severity level."""
        actual = actual_output["waiver_summary"]["waivers_by_severity"]
        expected = expected_output["waiver_summary"]["waivers_by_severity"]
        assert actual == expected, (
            f"Waivers by severity {actual} != expected {expected}"
        )

    def test_waivers_by_type(self, actual_output, expected_output):
        """Verify waiver counts broken down by control type."""
        actual = actual_output["waiver_summary"]["waivers_by_type"]
        expected = expected_output["waiver_summary"]["waivers_by_type"]
        assert actual == expected, (
            f"Waivers by type {actual} != expected {expected}"
        )

    def test_unique_waivers_used(self, actual_output, expected_output):
        """Verify the number of distinct waiver definitions that matched."""
        actual = actual_output["waiver_summary"]["unique_waivers_used"]
        expected = expected_output["waiver_summary"]["unique_waivers_used"]
        assert actual == expected, (
            f"Unique waivers used {actual} != expected {expected}"
        )


class TestMetadata:
    """Tests for evaluation metadata in the report."""

    def test_evaluation_profile(self, actual_output, expected_output):
        """Verify the evaluation profile used for the scan."""
        actual = actual_output["metadata"]["evaluation_profile"]
        expected = expected_output["metadata"]["evaluation_profile"]
        assert actual == expected, (
            f"Evaluation profile '{actual}' != expected '{expected}'"
        )

    def test_scoring_method(self, actual_output, expected_output):
        """Verify the scoring method reported in metadata."""
        actual = actual_output["metadata"]["scoring_method"]
        expected = expected_output["metadata"]["scoring_method"]
        assert actual == expected, (
            f"Scoring method '{actual}' != expected '{expected}'"
        )

    def test_fail_threshold(self, actual_output, expected_output):
        """Verify the failure threshold used for compliance determination."""
        actual = actual_output["metadata"]["fail_threshold"]
        expected = expected_output["metadata"]["fail_threshold"]
        assert math.isclose(actual, expected, rel_tol=1e-4), (
            f"Fail threshold {actual} != expected {expected}"
        )

    def test_inheritance_mode(self, actual_output, expected_output):
        """Verify the inheritance resolution mode reported."""
        actual = actual_output["metadata"]["inheritance_mode"]
        expected = expected_output["metadata"]["inheritance_mode"]
        assert actual == expected, (
            f"Inheritance mode '{actual}' != expected '{expected}'"
        )

    def test_exception_match_mode(self, actual_output, expected_output):
        """Verify the exception matching mode reported."""
        actual = actual_output["metadata"]["exception_match_mode"]
        expected = expected_output["metadata"]["exception_match_mode"]
        assert actual == expected, (
            f"Exception match mode '{actual}' != expected '{expected}'"
        )
