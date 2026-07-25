"""
Portfolio-level analytics for fixed-income portfolios.

Aggregates individual bond metrics into portfolio-level risk measures
including weighted average duration, portfolio convexity, total market
value, yield attribution, and risk decomposition.
"""

from typing import List, Dict, Any
import math


def compute_portfolio_weights(market_values: List[float]) -> List[float]:
    """
    Compute portfolio weights based on market values.

    Each bond's weight is its market value divided by total portfolio
    market value. Market values should be dirty (full) values to
    reflect actual economic exposure.

    Parameters
    ----------
    market_values : list of float
        Dirty market value of each position (quantity × dirty price)

    Returns
    -------
    list of float
        Portfolio weights summing to 1.0
    """
    total_mv = sum(market_values)
    if total_mv <= 0:
        return [0.0] * len(market_values)
    return [mv / total_mv for mv in market_values]


def compute_portfolio_duration(durations: List[float],
                               weights: List[float]) -> float:
    """
    Compute portfolio modified duration as weighted average.

    Parameters
    ----------
    durations : list of float
        Modified duration of each bond
    weights : list of float
        Portfolio weights

    Returns
    -------
    float
        Portfolio-level modified duration
    """
    return sum(d * w for d, w in zip(durations, weights))


def compute_portfolio_convexity(convexities: List[float],
                                weights: List[float]) -> float:
    """
    Compute portfolio convexity as weighted average.

    Parameters
    ----------
    convexities : list of float
        Convexity of each bond
    weights : list of float
        Portfolio weights

    Returns
    -------
    float
        Portfolio-level convexity
    """
    return sum(c * w for c, w in zip(convexities, weights))


def compute_portfolio_yield(ytms: List[float],
                            weights: List[float]) -> float:
    """
    Compute portfolio yield as market-value-weighted average of individual YTMs.

    Parameters
    ----------
    ytms : list of float
        YTM of each bond
    weights : list of float
        Portfolio weights

    Returns
    -------
    float
        Portfolio-level yield
    """
    return sum(y * w for y, w in zip(ytms, weights))


def compute_total_market_value(quantities: List[float],
                               dirty_prices: List[float],
                               face_values: List[float]) -> float:
    """
    Compute total portfolio market value.

    Market value per bond = quantity × (dirty_price / 100) × face_value
    (Assuming prices quoted per 100 of face value.)

    Parameters
    ----------
    quantities : list of float
        Number of bonds held
    dirty_prices : list of float
        Dirty prices per 100 face
    face_values : list of float
        Face value per bond

    Returns
    -------
    float
        Total portfolio market value
    """
    total = 0.0
    for qty, price, face in zip(quantities, dirty_prices, face_values):
        total += qty * (price / 100.0) * face
    return total


def compute_portfolio_dv01(durations: List[float],
                           market_values: List[float]) -> float:
    """
    Compute portfolio DV01 (dollar value of 1 basis point).

    DV01 = sum(ModDur_i × MV_i × 0.0001)

    Parameters
    ----------
    durations : list of float
        Modified duration of each bond
    market_values : list of float
        Market value of each position

    Returns
    -------
    float
        Portfolio DV01
    """
    total_dv01 = 0.0
    for dur, mv in zip(durations, market_values):
        total_dv01 += dur * mv * 0.0001
    return total_dv01


def compute_risk_contribution(durations: List[float],
                              weights: List[float],
                              portfolio_duration: float) -> List[float]:
    """
    Compute each bond's contribution to portfolio duration risk.

    Risk contribution = (weight × duration) / portfolio_duration

    Parameters
    ----------
    durations : list of float
        Modified duration per bond
    weights : list of float
        Portfolio weights
    portfolio_duration : float
        Total portfolio duration

    Returns
    -------
    list of float
        Fractional risk contribution per bond (sums to 1.0)
    """
    if portfolio_duration <= 0:
        return [0.0] * len(durations)

    contributions = []
    for d, w in zip(durations, weights):
        contributions.append((d * w) / portfolio_duration)
    return contributions


def compute_spread_duration(modified_durations: List[float],
                            spread_sensitivities: List[float],
                            weights: List[float]) -> float:
    """
    Compute portfolio spread duration.

    For corporate bonds, spread duration approximates sensitivity to
    credit spread changes. Uses modified duration scaled by spread
    sensitivity factor.

    Parameters
    ----------
    modified_durations : list of float
        Modified durations
    spread_sensitivities : list of float
        Spread sensitivity factors (typically close to 1.0 for investment grade)
    weights : list of float
        Portfolio weights

    Returns
    -------
    float
        Portfolio spread duration
    """
    total = 0.0
    for md, ss, w in zip(modified_durations, spread_sensitivities, weights):
        total += md * ss * w
    return total


def format_portfolio_report(bond_results: List[Dict[str, Any]],
                            portfolio_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format the final portfolio analytics report.

    Combines individual bond analytics with portfolio-level aggregates
    into the standardized output structure.

    Parameters
    ----------
    bond_results : list of dict
        Per-bond analytics results
    portfolio_metrics : dict
        Portfolio-level aggregated metrics

    Returns
    -------
    dict
        Complete portfolio analytics report
    """
    report = {
        "portfolio_summary": {
            "total_market_value": portfolio_metrics.get("total_market_value", 0.0),
            "portfolio_yield": portfolio_metrics.get("portfolio_yield", 0.0),
            "portfolio_modified_duration": portfolio_metrics.get("portfolio_duration", 0.0),
            "portfolio_convexity": portfolio_metrics.get("portfolio_convexity", 0.0),
            "portfolio_dv01": portfolio_metrics.get("portfolio_dv01", 0.0),
            "number_of_positions": len(bond_results)
        },
        "bond_analytics": bond_results,
        "risk_decomposition": {
            "duration_contributions": portfolio_metrics.get("risk_contributions", []),
            "largest_risk_contributor": _find_largest_contributor(
                bond_results, portfolio_metrics.get("risk_contributions", [])
            )
        }
    }
    return report


def _find_largest_contributor(bond_results: List[Dict[str, Any]],
                              contributions: List[float]) -> str:
    """Identify the bond with the largest duration risk contribution."""
    if not contributions or not bond_results:
        return "N/A"

    max_idx = 0
    max_val = contributions[0] if contributions else 0.0
    for i, c in enumerate(contributions):
        if c > max_val:
            max_val = c
            max_idx = i

    if max_idx < len(bond_results):
        return bond_results[max_idx].get("bond_id", f"bond_{max_idx}")
    return "N/A"
