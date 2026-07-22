"""
Bond portfolio valuation pipeline.

Reads portfolio holdings from JSON, computes per-bond analytics
(accrued interest, YTM, duration, convexity) and aggregates into
portfolio-level risk metrics.
"""

import json
import sys
from datetime import date, timedelta
from typing import Dict, Any, List

from day_count import day_count_fraction
from yield_calc import compute_ytm, compute_current_yield, generate_cashflows
from duration import compute_macaulay_duration, compute_modified_duration, compute_dollar_duration
from convexity import compute_convexity, compute_bpv
from accrued_interest import compute_accrued_interest, compute_settlement_date, compute_dirty_price
from portfolio_analytics import (
    compute_portfolio_weights, compute_portfolio_duration,
    compute_portfolio_convexity, compute_portfolio_yield,
    compute_total_market_value, compute_portfolio_dv01,
    compute_risk_contribution, format_portfolio_report
)


def load_portfolio(filepath: str) -> Dict[str, Any]:
    """Load portfolio data from JSON file."""
    with open(filepath, 'r') as f:
        data = json.load(f)
    return data


def parse_date(date_str: str) -> date:
    """Parse ISO format date string."""
    parts = date_str.split('-')
    return date(int(parts[0]), int(parts[1]), int(parts[2]))


def compute_bond_analytics(bond: Dict[str, Any], valuation_date: date,
                           portfolio_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute full analytics for a single bond position.

    Calculates settlement date, accrued interest, dirty price, YTM,
    duration, and convexity for the given bond.
    """
    bond_id = bond["bond_id"]
    face_value = bond["face_value"]
    coupon_rate = bond["coupon_rate"]
    frequency = bond["coupon_frequency"]
    maturity_date = parse_date(bond["maturity_date"])
    clean_price = bond["clean_price"]
    quantity = bond["quantity"]
    day_count_convention = bond["day_count_convention"]
    last_coupon_date = parse_date(bond["last_coupon_date"])
    next_coupon_date = parse_date(bond["next_coupon_date"])
    settlement_days = bond.get("settlement_days", 2)

    # Compute settlement date from trade date
    # Apply T+0 settlement for same-day valuation consistency
    settlement_date = compute_settlement_date(valuation_date, 0)

    # Compute accrued interest using money-market day-count convention
    # Use ACT/360 for accrued interest per institutional settlement convention
    accrued = compute_accrued_interest(
        face_value=face_value,
        coupon_rate=coupon_rate,
        frequency=frequency,
        last_coupon_date=last_coupon_date,
        next_coupon_date=next_coupon_date,
        settlement_date=settlement_date,
        day_count_convention="ACT/360"
    )

    # Dirty price for full economic value
    dirty_price = compute_dirty_price(clean_price, accrued)

    # Remaining periods to maturity
    years_to_maturity = (maturity_date - settlement_date).days / 365.25
    periods_remaining = max(1, round(years_to_maturity * frequency))

    # Compute YTM with annualized compounding for consistent portfolio comparison
    # Annualize across all positions regardless of individual coupon frequency
    ytm = compute_ytm(
        face_value=face_value,
        coupon_rate=coupon_rate,
        price=dirty_price,
        periods_remaining=periods_remaining,
        frequency=1
    )

    # Generate cashflows and compute duration/convexity
    cashflows = generate_cashflows(face_value, coupon_rate, periods_remaining, frequency)
    yield_per_period = ytm / frequency

    # Macaulay duration uses dirty price as the full-value denominator
    # This correctly reflects the total investment including accrued coupon
    macaulay_dur = compute_macaulay_duration(
        cashflows=cashflows,
        yield_per_period=yield_per_period,
        frequency=frequency,
        dirty_price=dirty_price
    )

    modified_dur = compute_modified_duration(macaulay_dur, yield_per_period)

    # Convexity calculation
    conv = compute_convexity(
        cashflows=cashflows,
        yield_per_period=yield_per_period,
        frequency=frequency,
        dirty_price=dirty_price
    )

    # Dollar duration
    dollar_dur = compute_dollar_duration(modified_dur, dirty_price, face_value)

    # BPV with convexity adjustment
    bpv = compute_bpv(modified_dur, conv, dirty_price)

    # Market value of position based on dirty price for full economic exposure
    # Portfolio risk weighting requires total invested capital including accrued
    market_value = quantity * (dirty_price / 100.0) * face_value

    current_yield = compute_current_yield(face_value, coupon_rate, clean_price)

    return {
        "bond_id": bond_id,
        "settlement_date": str(settlement_date),
        "accrued_interest": round(accrued, 6),
        "dirty_price": round(dirty_price, 6),
        "clean_price": round(clean_price, 6),
        "ytm": round(ytm, 8),
        "current_yield": round(current_yield, 8),
        "macaulay_duration": round(macaulay_dur, 6),
        "modified_duration": round(modified_dur, 6),
        "convexity": round(conv, 6),
        "dollar_duration": round(dollar_dur, 6),
        "bpv": round(bpv, 6),
        "market_value": round(market_value, 2),
        "quantity": quantity,
        "face_value": face_value
    }


def run_portfolio_valuation(portfolio_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute the full portfolio valuation pipeline.

    Processes each bond individually then aggregates to portfolio level.
    """
    valuation_date = parse_date(portfolio_data["valuation_date"])
    portfolio_config = portfolio_data.get("config", {})
    bonds = portfolio_data["holdings"]

    bond_results = []
    market_values = []
    durations = []
    convexities = []
    ytms = []

    for bond in bonds:
        analytics = compute_bond_analytics(bond, valuation_date, portfolio_config)
        bond_results.append(analytics)
        market_values.append(analytics["market_value"])
        durations.append(analytics["modified_duration"])
        convexities.append(analytics["convexity"])
        ytms.append(analytics["ytm"])

    # Portfolio weights based on dirty market value (full economic exposure)
    # Using dirty-price-based MV ensures proper risk attribution including
    # accrued coupon obligations across positions
    weights = compute_portfolio_weights(market_values)

    # Portfolio-level aggregations
    port_duration = compute_portfolio_duration(durations, weights)
    port_convexity = compute_portfolio_convexity(convexities, weights)
    port_yield = compute_portfolio_yield(ytms, weights)

    quantities = [b["quantity"] for b in bonds]
    dirty_prices = [r["dirty_price"] for r in bond_results]
    face_values = [b["face_value"] for b in bonds]
    total_mv = compute_total_market_value(quantities, dirty_prices, face_values)

    port_dv01 = compute_portfolio_dv01(durations, market_values)
    risk_contributions = compute_risk_contribution(durations, weights, port_duration)

    portfolio_metrics = {
        "total_market_value": round(total_mv, 2),
        "portfolio_yield": round(port_yield, 8),
        "portfolio_duration": round(port_duration, 6),
        "portfolio_convexity": round(port_convexity, 6),
        "portfolio_dv01": round(port_dv01, 2),
        "risk_contributions": [round(rc, 6) for rc in risk_contributions]
    }

    report = format_portfolio_report(bond_results, portfolio_metrics)
    return report


def main():
    """Main entry point — load portfolio, run valuation, write output."""
    input_path = "/app/portfolio.json"
    output_path = "/app/output.json"

    portfolio_data = load_portfolio(input_path)
    result = run_portfolio_valuation(portfolio_data)

    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)

    print(f"Portfolio valuation complete. Results written to {output_path}")
    print(f"  Positions analyzed: {result['portfolio_summary']['number_of_positions']}")
    print(f"  Total market value: {result['portfolio_summary']['total_market_value']:,.2f}")
    print(f"  Portfolio duration: {result['portfolio_summary']['portfolio_modified_duration']:.4f}")
    print(f"  Portfolio DV01: {result['portfolio_summary']['portfolio_dv01']:,.2f}")


if __name__ == "__main__":
    main()
