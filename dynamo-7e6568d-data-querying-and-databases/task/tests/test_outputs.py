"""Tests for graph analysis pipeline output correctness."""

import json
import pytest


@pytest.fixture
def actual_output():
    """Load the pipeline output."""
    with open("/app/output.json", "r") as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected correct output."""
    with open("/tests/expected_output.json", "r") as f:
        return json.load(f)


class TestGraphSummary:
    """Tests for graph summary section."""

    def test_node_count(self, actual_output, expected_output):
        """Verify the total number of nodes in the graph."""
        assert actual_output["graph_summary"]["node_count"] == expected_output["graph_summary"]["node_count"]

    def test_edge_count(self, actual_output, expected_output):
        """Verify the total number of edges in the graph."""
        assert actual_output["graph_summary"]["edge_count"] == expected_output["graph_summary"]["edge_count"]

    def test_type_distribution(self, actual_output, expected_output):
        """Verify the node type distribution matches expected counts."""
        assert actual_output["graph_summary"]["type_distribution"] == expected_output["graph_summary"]["type_distribution"]

    def test_density(self, actual_output, expected_output):
        """Verify the graph density computation."""
        assert abs(actual_output["graph_summary"]["density"] - expected_output["graph_summary"]["density"]) < 1e-4

    def test_reciprocity(self, actual_output, expected_output):
        """Verify the edge reciprocity computation."""
        assert abs(actual_output["graph_summary"]["reciprocity"] - expected_output["graph_summary"]["reciprocity"]) < 1e-4


class TestBetweennessCentrality:
    """Tests for betweenness centrality analysis results."""

    def test_top_k_nodes(self, actual_output, expected_output):
        """Verify the top-k highest betweenness nodes are identified correctly."""
        actual_nodes = [entry["node"] for entry in actual_output["betweenness_centrality"]["top_k"]]
        expected_nodes = [entry["node"] for entry in expected_output["betweenness_centrality"]["top_k"]]
        assert actual_nodes == expected_nodes

    def test_top_k_scores(self, actual_output, expected_output):
        """Verify betweenness centrality scores match expected values within tolerance."""
        for actual, expected in zip(
            actual_output["betweenness_centrality"]["top_k"],
            expected_output["betweenness_centrality"]["top_k"]
        ):
            assert abs(actual["score"] - expected["score"]) < 1e-4

    def test_average_path_length(self, actual_output, expected_output):
        """Verify the average shortest path length across all reachable pairs."""
        assert abs(
            actual_output["betweenness_centrality"]["average_path_length"] -
            expected_output["betweenness_centrality"]["average_path_length"]
        ) < 1e-4


class TestPageRank:
    """Tests for PageRank influence scoring results."""

    def test_top_k_nodes(self, actual_output, expected_output):
        """Verify the top-k highest PageRank nodes are identified correctly."""
        actual_nodes = [entry["node"] for entry in actual_output["pagerank"]["top_k"]]
        expected_nodes = [entry["node"] for entry in expected_output["pagerank"]["top_k"]]
        assert actual_nodes == expected_nodes

    def test_top_k_scores(self, actual_output, expected_output):
        """Verify PageRank scores match expected values within tolerance."""
        for actual, expected in zip(
            actual_output["pagerank"]["top_k"],
            expected_output["pagerank"]["top_k"]
        ):
            assert abs(actual["score"] - expected["score"]) < 1e-4

    def test_iteration_count(self, actual_output, expected_output):
        """Verify the number of PageRank iterations until convergence."""
        assert actual_output["pagerank"]["iteration_count"] == expected_output["pagerank"]["iteration_count"]


class TestClustering:
    """Tests for directed clustering coefficient results."""

    def test_all_coefficients(self, actual_output, expected_output):
        """Verify clustering coefficient for each node matches expected value."""
        for node, expected_val in expected_output["clustering"]["coefficients"].items():
            actual_val = actual_output["clustering"]["coefficients"].get(node, -1)
            assert abs(actual_val - expected_val) < 1e-4, f"Node {node}: {actual_val} != {expected_val}"

    def test_average_clustering(self, actual_output, expected_output):
        """Verify the average clustering coefficient across all nodes."""
        assert abs(
            actual_output["clustering"]["average"] -
            expected_output["clustering"]["average"]
        ) < 1e-4

    def test_scc_sizes(self, actual_output, expected_output):
        """Verify strongly connected component sizes match expected values."""
        assert sorted(actual_output["clustering"]["scc_sizes"], reverse=True) == \
               sorted(expected_output["clustering"]["scc_sizes"], reverse=True)


class TestInfluenceSpread:
    """Tests for influence spread analysis results."""

    def test_seed_nodes(self, actual_output, expected_output):
        """Verify the seed nodes used for influence propagation."""
        assert actual_output["influence_spread"]["seeds"] == expected_output["influence_spread"]["seeds"]

    def test_total_influence(self, actual_output, expected_output):
        """Verify the total accumulated influence across all nodes."""
        assert abs(
            actual_output["influence_spread"]["total_influence"] -
            expected_output["influence_spread"]["total_influence"]
        ) < 1e-4

    def test_top_k_nodes(self, actual_output, expected_output):
        """Verify the top-k most influenced nodes are identified correctly."""
        actual_nodes = [entry["node"] for entry in actual_output["influence_spread"]["top_k"]]
        expected_nodes = [entry["node"] for entry in expected_output["influence_spread"]["top_k"]]
        assert actual_nodes == expected_nodes

    def test_top_k_influence_scores(self, actual_output, expected_output):
        """Verify influence spread scores match expected values within tolerance."""
        for actual, expected in zip(
            actual_output["influence_spread"]["top_k"],
            expected_output["influence_spread"]["top_k"]
        ):
            assert abs(actual["influence"] - expected["influence"]) < 1e-4
