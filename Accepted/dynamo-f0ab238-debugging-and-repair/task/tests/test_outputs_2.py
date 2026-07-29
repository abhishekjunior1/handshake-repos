"""Tests for service mesh pipeline output on second hidden configuration."""

import json
import os

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = "/app/output.json"
EXPECTED_PATH = os.path.join(TESTS_DIR, "expected_output_2.json")


def load_output():
    """Load the pipeline output."""
    with open(OUTPUT_PATH) as f:
        return json.load(f)


def load_expected():
    """Load the expected output for config 2."""
    with open(EXPECTED_PATH) as f:
        return json.load(f)


def approx_equal(a, b, rel_tol=1e-4):
    """Check approximate equality for floating point values."""
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if b == 0:
            return abs(a) < 1e-6
        return abs(a - b) / max(abs(b), 1e-10) < rel_tol
    return a == b


class TestEvaluationSummary2:
    """Tests for evaluation summary on second config."""

    def test_total_requests(self):
        """Verify total requests evaluated on second config."""
        output = load_output()
        expected = load_expected()
        assert output["evaluation_summary"]["total_requests_evaluated"] == \
            expected["evaluation_summary"]["total_requests_evaluated"]

    def test_denied_count(self):
        """Verify denied request count on second config."""
        output = load_output()
        expected = load_expected()
        assert output["evaluation_summary"]["requests_denied"] == \
            expected["evaluation_summary"]["requests_denied"]

    def test_mesh_health_score(self):
        """Verify mesh health score on second config."""
        output = load_output()
        expected = load_expected()
        assert approx_equal(
            output["evaluation_summary"]["mesh_health_score"],
            expected["evaluation_summary"]["mesh_health_score"]
        )


class TestServiceHealth2:
    """Tests for service health on second config."""

    def test_service_health_values(self):
        """Verify aggregate health for all services on second config."""
        output = load_output()
        expected = load_expected()
        for service_id in expected["service_health"]:
            exp_h = expected["service_health"][service_id]
            out_h = output["service_health"][service_id]
            assert approx_equal(
                out_h["aggregate_health"],
                exp_h["aggregate_health"]
            ), f"Health mismatch for {service_id}: got {out_h['aggregate_health']}, expected {exp_h['aggregate_health']}"

    def test_endpoint_status_counts(self):
        """Verify healthy/unhealthy endpoint counts on second config."""
        output = load_output()
        expected = load_expected()
        for service_id in expected["service_health"]:
            exp_h = expected["service_health"][service_id]
            out_h = output["service_health"][service_id]
            assert out_h["unhealthy_endpoints"] == exp_h["unhealthy_endpoints"], \
                f"{service_id}: got {out_h['unhealthy_endpoints']} unhealthy, expected {exp_h['unhealthy_endpoints']}"


class TestRoutingDecisions2:
    """Tests for routing decisions on second config."""

    def test_selected_upstreams(self):
        """Verify selected upstreams on second config."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert out_d["selected_upstream"] == exp_d["selected_upstream"], \
                f"Request {out_d['request_id']}: got '{out_d['selected_upstream']}', expected '{exp_d['selected_upstream']}'"

    def test_load_balancer_weights(self):
        """Verify load balancer weights on second config."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert approx_equal(
                out_d["load_balancer_weight"],
                exp_d["load_balancer_weight"]
            ), f"Request {out_d['request_id']}: weight {out_d['load_balancer_weight']} != expected {exp_d['load_balancer_weight']}"

    def test_policy_decisions(self):
        """Verify policy decisions on second config."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert out_d["policy_decision"] == exp_d["policy_decision"], \
                f"Request {out_d['request_id']}: got '{out_d['policy_decision']}', expected '{exp_d['policy_decision']}'"

    def test_tls_modes(self):
        """Verify TLS modes on second config."""
        output = load_output()
        expected = load_expected()
        for out_d, exp_d in zip(output["routing_decisions"], expected["routing_decisions"]):
            assert out_d["tls_mode"] == exp_d["tls_mode"], \
                f"Request {out_d['request_id']}: got '{out_d['tls_mode']}', expected '{exp_d['tls_mode']}'"
