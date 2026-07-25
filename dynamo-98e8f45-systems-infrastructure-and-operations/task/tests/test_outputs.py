"""Verification tests for K8s pod scheduling simulator (hidden config 1)."""

import json
import os
import pytest

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.fixture
def actual_output():
    """Load the pipeline output produced by the agent's code."""
    with open("/app/output.json") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected correct output for hidden config 1."""
    with open(os.path.join(TESTS_DIR, "expected_output_1.json")) as f:
        return json.load(f)


class TestSchedulingSummary:
    """Tests for overall scheduling summary statistics."""

    def test_total_pods(self, actual_output, expected_output):
        """Verify the total number of pods processed matches expected."""
        assert actual_output["scheduling_summary"]["total_pods"] == expected_output["scheduling_summary"]["total_pods"]

    def test_scheduled_count(self, actual_output, expected_output):
        """Verify the number of successfully scheduled pods."""
        assert actual_output["scheduling_summary"]["scheduled"] == expected_output["scheduling_summary"]["scheduled"]

    def test_preempting_count(self, actual_output, expected_output):
        """Verify the number of pods requiring preemption."""
        assert actual_output["scheduling_summary"]["preempting"] == expected_output["scheduling_summary"]["preempting"]

    def test_unschedulable_count(self, actual_output, expected_output):
        """Verify the number of unschedulable pods."""
        assert actual_output["scheduling_summary"]["unschedulable"] == expected_output["scheduling_summary"]["unschedulable"]

    def test_scheduling_rate(self, actual_output, expected_output):
        """Verify the scheduling success rate."""
        assert actual_output["scheduling_summary"]["scheduling_rate"] == expected_output["scheduling_summary"]["scheduling_rate"]


class TestPodDecisions:
    """Tests for individual pod scheduling decisions."""

    def test_pod_count_matches(self, actual_output, expected_output):
        """Verify same number of pod decisions in output."""
        assert len(actual_output["pod_decisions"]) == len(expected_output["pod_decisions"])

    def test_pod_phases(self, actual_output, expected_output):
        """Verify each pod's scheduling phase (Scheduled/Preempting/Unschedulable)."""
        actual_phases = {d["pod_name"]: d["phase"] for d in actual_output["pod_decisions"]}
        expected_phases = {d["pod_name"]: d["phase"] for d in expected_output["pod_decisions"]}
        assert actual_phases == expected_phases

    def test_pod_node_assignments(self, actual_output, expected_output):
        """Verify each pod is assigned to the correct node."""
        actual_nodes = {d["pod_name"]: d["selected_node"] for d in actual_output["pod_decisions"]}
        expected_nodes = {d["pod_name"]: d["selected_node"] for d in expected_output["pod_decisions"]}
        assert actual_nodes == expected_nodes

    def test_score_breakdowns(self, actual_output, expected_output):
        """Verify the scoring breakdown for each pod's candidate nodes."""
        for actual_pod, expected_pod in zip(actual_output["pod_decisions"], expected_output["pod_decisions"]):
            assert actual_pod["score_breakdown"] == expected_pod["score_breakdown"], \
                f"Score mismatch for {actual_pod['pod_name']}"

    def test_filtered_nodes(self, actual_output, expected_output):
        """Verify which nodes were filtered and for what reasons."""
        for actual_pod, expected_pod in zip(actual_output["pod_decisions"], expected_output["pod_decisions"]):
            actual_filtered = sorted([f["node"] for f in actual_pod.get("filtered_nodes", [])])
            expected_filtered = sorted([f["node"] for f in expected_pod.get("filtered_nodes", [])])
            assert actual_filtered == expected_filtered, \
                f"Filtered nodes mismatch for {actual_pod['pod_name']}"


class TestNodePlacements:
    """Tests for per-node pod placement results."""

    def test_node_placements(self, actual_output, expected_output):
        """Verify the per-node placement summary matches expected."""
        assert actual_output["node_placements"] == expected_output["node_placements"]


class TestClusterInfo:
    """Tests for cluster metadata in the report."""

    def test_cluster_info(self, actual_output, expected_output):
        """Verify cluster info section is correct."""
        assert actual_output["cluster_info"] == expected_output["cluster_info"]
