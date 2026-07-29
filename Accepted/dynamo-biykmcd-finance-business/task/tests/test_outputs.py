"""
Verifier for bond portfolio valuation pipeline.

Compares the pipeline's output on hidden test data against expected results.
Tests cover portfolio-level metrics, individual bond analytics, and
risk decomposition accuracy.
"""

import json
import math
import pytest


EXPECTED_PATH = "/app/expected_output.json"
OUTPUT_PATH = "/app/output.json"
REL_TOL = 1e-4


def load_json(path):
    """Load JSON from file path."""
    with open(path, 'r') as f:
        return json.load(f)


@pytest.fixture
def expected_output():
    """Load the expected output from the reference file."""
    return load_json(EXPECTED_PATH)


@pytest.fixture
def actual_output():
    """Load the actual pipeline output."""
    return load_json(OUTPUT_PATH)


def approx_equal(actual, expected, rel_tol=REL_TOL):
    """Check if two numeric values are approximately equal within relative tolerance."""
    if expected == 0:
        return abs(actual) < 1e-6
    return abs(actual - expected) / abs(expected) <= rel_tol


class TestPortfolioSummary:
    """Tests for portfolio-level summary metrics."""

    def test_total_market_value(self, actual_output, expected_output):
        """Verify total portfolio market value matches expected within tolerance."""
        actual = actual_output["portfolio_summary"]["total_market_value"]
        expected = expected_output["portfolio_summary"]["total_market_value"]
        assert approx_equal(actual, expected), (
            f"Total market value mismatch: got {actual}, expected {expected}"
        )

    def test_portfolio_yield(self, actual_output, expected_output):
        """Verify portfolio-level weighted yield matches expected."""
        actual = actual_output["portfolio_summary"]["portfolio_yield"]
        expected = expected_output["portfolio_summary"]["portfolio_yield"]
        assert approx_equal(actual, expected), (
            f"Portfolio yield mismatch: got {actual}, expected {expected}"
        )

    def test_portfolio_modified_duration(self, actual_output, expected_output):
        """Verify portfolio modified duration is correctly aggregated."""
        actual = actual_output["portfolio_summary"]["portfolio_modified_duration"]
        expected = expected_output["portfolio_summary"]["portfolio_modified_duration"]
        assert approx_equal(actual, expected), (
            f"Portfolio duration mismatch: got {actual}, expected {expected}"
        )

    def test_portfolio_convexity(self, actual_output, expected_output):
        """Verify portfolio convexity is correctly aggregated."""
        actual = actual_output["portfolio_summary"]["portfolio_convexity"]
        expected = expected_output["portfolio_summary"]["portfolio_convexity"]
        assert approx_equal(actual, expected), (
            f"Portfolio convexity mismatch: got {actual}, expected {expected}"
        )

    def test_portfolio_dv01(self, actual_output, expected_output):
        """Verify portfolio DV01 calculation matches expected."""
        actual = actual_output["portfolio_summary"]["portfolio_dv01"]
        expected = expected_output["portfolio_summary"]["portfolio_dv01"]
        assert approx_equal(actual, expected), (
            f"Portfolio DV01 mismatch: got {actual}, expected {expected}"
        )

    def test_number_of_positions(self, actual_output, expected_output):
        """Verify all positions are processed."""
        actual = actual_output["portfolio_summary"]["number_of_positions"]
        expected = expected_output["portfolio_summary"]["number_of_positions"]
        assert actual == expected, (
            f"Position count mismatch: got {actual}, expected {expected}"
        )


class TestBondAnalytics:
    """Tests for individual bond-level analytics."""

    def test_bond_count_matches(self, actual_output, expected_output):
        """Verify the correct number of bonds are in the output."""
        actual_count = len(actual_output["bond_analytics"])
        expected_count = len(expected_output["bond_analytics"])
        assert actual_count == expected_count, (
            f"Bond analytics count mismatch: got {actual_count}, expected {expected_count}"
        )

    def test_settlement_dates(self, actual_output, expected_output):
        """Verify settlement dates are correctly computed with proper T+N offset."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            assert actual_bond["settlement_date"] == expected_bond["settlement_date"], (
                f"Settlement date mismatch for {expected_bond['bond_id']}: "
                f"got {actual_bond['settlement_date']}, expected {expected_bond['settlement_date']}"
            )

    def test_accrued_interest(self, actual_output, expected_output):
        """Verify accrued interest uses correct day-count convention per bond."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            actual_ai = actual_bond["accrued_interest"]
            expected_ai = expected_bond["accrued_interest"]
            if expected_ai == 0:
                assert abs(actual_ai) < 1e-6, (
                    f"Accrued interest for {expected_bond['bond_id']} should be 0, got {actual_ai}"
                )
            else:
                assert approx_equal(actual_ai, expected_ai), (
                    f"Accrued interest mismatch for {expected_bond['bond_id']}: "
                    f"got {actual_ai}, expected {expected_ai}"
                )

    def test_dirty_prices(self, actual_output, expected_output):
        """Verify dirty prices reflect correct accrued interest addition."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            assert approx_equal(actual_bond["dirty_price"], expected_bond["dirty_price"]), (
                f"Dirty price mismatch for {expected_bond['bond_id']}: "
                f"got {actual_bond['dirty_price']}, expected {expected_bond['dirty_price']}"
            )

    def test_ytm_values(self, actual_output, expected_output):
        """Verify yield-to-maturity uses correct compounding frequency."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            assert approx_equal(actual_bond["ytm"], expected_bond["ytm"]), (
                f"YTM mismatch for {expected_bond['bond_id']}: "
                f"got {actual_bond['ytm']}, expected {expected_bond['ytm']}"
            )

    def test_modified_duration(self, actual_output, expected_output):
        """Verify modified duration calculation for each bond."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            assert approx_equal(
                actual_bond["modified_duration"], expected_bond["modified_duration"]
            ), (
                f"Modified duration mismatch for {expected_bond['bond_id']}: "
                f"got {actual_bond['modified_duration']}, expected {expected_bond['modified_duration']}"
            )

    def test_convexity(self, actual_output, expected_output):
        """Verify convexity calculation for each bond."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            assert approx_equal(actual_bond["convexity"], expected_bond["convexity"]), (
                f"Convexity mismatch for {expected_bond['bond_id']}: "
                f"got {actual_bond['convexity']}, expected {expected_bond['convexity']}"
            )

    def test_market_values(self, actual_output, expected_output):
        """Verify position market values use correct dirty price."""
        for actual_bond, expected_bond in zip(
            actual_output["bond_analytics"], expected_output["bond_analytics"]
        ):
            assert approx_equal(actual_bond["market_value"], expected_bond["market_value"]), (
                f"Market value mismatch for {expected_bond['bond_id']}: "
                f"got {actual_bond['market_value']}, expected {expected_bond['market_value']}"
            )


class TestRiskDecomposition:
    """Tests for portfolio risk decomposition."""

    def test_duration_contributions_sum(self, actual_output, expected_output):
        """Verify duration contributions sum to approximately 1.0."""
        contributions = actual_output["risk_decomposition"]["duration_contributions"]
        total = sum(contributions)
        assert approx_equal(total, 1.0, rel_tol=1e-3), (
            f"Duration contributions should sum to 1.0, got {total}"
        )

    def test_duration_contributions_values(self, actual_output, expected_output):
        """Verify individual duration risk contributions match expected."""
        actual_contribs = actual_output["risk_decomposition"]["duration_contributions"]
        expected_contribs = expected_output["risk_decomposition"]["duration_contributions"]
        for i, (actual, expected) in enumerate(zip(actual_contribs, expected_contribs)):
            assert approx_equal(actual, expected), (
                f"Duration contribution [{i}] mismatch: got {actual}, expected {expected}"
            )

    def test_largest_risk_contributor(self, actual_output, expected_output):
        """Verify the largest risk contributor is correctly identified."""
        actual = actual_output["risk_decomposition"]["largest_risk_contributor"]
        expected = expected_output["risk_decomposition"]["largest_risk_contributor"]
        assert actual == expected, (
            f"Largest risk contributor mismatch: got '{actual}', expected '{expected}'"
        )
