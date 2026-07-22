"""Tests for service mesh traffic policy evaluation pipeline output."""

import json
import os
import math

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output.json")


def load_output():
    """Load the pipeline output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4):
    """Check approximate equality for floating point values."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if b == 0:
            return abs(a) < 1e-6
        return abs(a - b) / max(abs(b), 1e-10) < rel_tol
    return a == b


class TestEvaluationSummary:
    """Tests for the evaluation summary section."""

    def test_total_requests(self):
        """Verify total number of requests evaluated matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["evaluation_summary"]["total_requests_evaluated"] == \
            expected["evaluation_summary"]["total_requests_evaluated"]

    def test_allowed_count(self):
        """Verify count of allowed requests matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["evaluation_summary"]["requests_allowed"] == \
            expected["evaluation_summary"]["requests_allowed"]

    def test_denied_count(self):
        """Verify count of denied requests matches expected."""
        output = load_output()
        expected = load_expected()
        assert output["evaluation_summary"]["requests_denied"] == \
            expected["evaluation_summary"]["requests_denied"]

    def test_allow_rate(self):
        """Verify allow rate percentage matches expected."""
        output = load_output()
        expected = load_expected()
        assert approx_equal(
            output["evaluation_summary"]["allow_rate_percent"],
            expected["evaluation_summary"]["allow_rate_percent"]
        )

    def test_mesh_health_score(self):
        """Verify mesh health score matches expected."""
        output = load_output()
        expected = load_expected()
        assert approx_equal(
            output["evaluation_summary"]["mesh_health_score"],
            expected["evaluation_summary"]["mesh_health_score"]
        )

    def test_average_policy_score(self):
        """Verify average policy score matches expected."""
        output = load_output()
        expected = load_expected()
        assert approx_equal(
            output["evaluation_summary"]["average_policy_score"],
            expected["evaluation_summary"]["average_policy_score"]
        )


class TestServiceHealth:
    """Tests for service health section."""

    def test_service_health_keys(self):
        """Verify all expected services are present in health report."""
        output = load_output()
        expected = load_expected()
        assert set(output["service_health"].keys()) == set(expected["service_health"].keys())

    def test_service_health_values(self):
        """Verify aggregate health values match expected for all services."""
        output = load_output()
        expected = load_expected()
        for service_id in expected["service_health"]:
            exp_health = expected["service_health"][service_id]
            out_health = output["service_health"][service_id]
            assert approx_equal(
                out_health["aggregate_health"],
                exp_health["aggregate_health"]
            ), f"Health mismatch for {service_id}: got {out_health['aggregate_health']}, expected {exp_health['aggregate_health']}"

    def test_endpoint_counts(self):
        """Verify endpoint status counts match expected for all services."""
        output = load_output()
        expected = load_expected()
        for service_id in expected["service_health"]:
            exp_h = expected["service_health"][service_id]
            out_h = output["service_health"][service_id]
            assert out_h["healthy_endpoints"] == exp_h["healthy_endpoints"], \
                f"{service_id} healthy: got {out_h['healthy_endpoints']}, expected {exp_h['healthy_endpoints']}"
            assert out_h["unhealthy_endpoints"] == exp_h["unhealthy_endpoints"], \
                f"{service_id} unhealthy: got {out_h['unhealthy_endpoints']}, expected {exp_h['unhealthy_endpoints']}"


class TestRoutingDecisions:
    """Tests for individual routing decisions."""

    def test_routing_decision_count(self):
        """Verify correct number of routing decisions."""
        output = load_output()
        expected = load_expected()
        assert len(output["routing_decisions"]) == len(expected["routing_decisions"])

    def test_selected_upstreams(self):
        """Verify selected upstream endpoints match expected for each request."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert out_d["selected_upstream"] == exp_d["selected_upstream"], \
                f"Request {out_d['request_id']}: got upstream '{out_d['selected_upstream']}', expected '{exp_d['selected_upstream']}'"

    def test_load_balancer_weights(self):
        """Verify load balancer weights match expected values."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert approx_equal(
                out_d["load_balancer_weight"],
                exp_d["load_balancer_weight"]
            ), f"Request {out_d['request_id']}: weight {out_d['load_balancer_weight']} != expected {exp_d['load_balancer_weight']}"

    def test_policy_decisions(self):
        """Verify policy decisions (allow/deny) match expected."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert out_d["policy_decision"] == exp_d["policy_decision"], \
                f"Request {out_d['request_id']}: got '{out_d['policy_decision']}', expected '{exp_d['policy_decision']}'"

    def test_tls_modes(self):
        """Verify TLS mode assignments match expected."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert out_d["tls_mode"] == exp_d["tls_mode"], \
                f"Request {out_d['request_id']}: got tls '{out_d['tls_mode']}', expected '{exp_d['tls_mode']}'"

    def test_tls_overhead(self):
        """Verify TLS overhead values match expected."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert approx_equal(
                out_d["tls_overhead_ms"],
                exp_d["tls_overhead_ms"]
            ), f"Request {out_d['request_id']}: tls_overhead {out_d['tls_overhead_ms']} != expected {exp_d['tls_overhead_ms']}"


class TestPolicyEnforcement:
    """Tests for policy enforcement summary."""

    def test_policy_totals(self):
        """Verify policy enforcement total counts match expected."""
        output = load_output()
        expected = load_expected()
        assert output["policy_enforcement"]["total_evaluations"] == \
            expected["policy_enforcement"]["total_evaluations"]
        assert output["policy_enforcement"]["allowed"] == \
            expected["policy_enforcement"]["allowed"]
        assert output["policy_enforcement"]["denied"] == \
            expected["policy_enforcement"]["denied"]

    def test_policy_scores(self):
        """Verify policy enforcement scores match expected."""
        output = load_output()
        expected = load_expected()
        assert approx_equal(
            output["policy_enforcement"]["average_policy_score"],
            expected["policy_enforcement"]["average_policy_score"]
        )
        assert approx_equal(
            output["policy_enforcement"]["mesh_health_score"],
            expected["policy_enforcement"]["mesh_health_score"]
        )
