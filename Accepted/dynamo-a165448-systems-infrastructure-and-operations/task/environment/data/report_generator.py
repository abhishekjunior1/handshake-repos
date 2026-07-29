"""
Report generator for storage tiering analysis output.

Formats all analysis results into the final JSON output structure
including tier utilization, heat distribution, wear metrics,
promotion scores, migration plan, and overall health indicators.
"""

import json
from typing import Any


def generate_tier_report(tier_utilization: dict[str, dict],
                         heat_distribution: dict[str, int],
                         wear_metrics: list[dict],
                         migration_summary: dict[str, Any],
                         tier_balance_score: float,
                         promotion_scores: list[dict],
                         migrations: list[dict]) -> dict[str, Any]:
    """
    Generate the complete tiering analysis report.

    Args:
        tier_utilization: per-tier capacity metrics
        heat_distribution: hot/warm/cold block counts
        wear_metrics: per-device wear analysis results
        migration_summary: migration plan statistics
        tier_balance_score: alignment score [0, 1]
        promotion_scores: all block promotion scores
        migrations: planned migration operations

    Returns:
        Complete report dict ready for JSON serialization.
    """
    # Compute health indicators
    health = compute_health_indicators(
        tier_utilization, wear_metrics, tier_balance_score
    )

    # Format wear metrics for output
    formatted_wear = format_wear_metrics(wear_metrics)

    # Top promotion candidates (top 10 by score)
    top_promotions = promotion_scores[:10] if promotion_scores else []

    report = {
        "tier_utilization": tier_utilization,
        "heat_distribution": heat_distribution,
        "wear_metrics": formatted_wear,
        "migration_plan": {
            "summary": migration_summary,
            "operations": migrations,
        },
        "tier_balance_score": tier_balance_score,
        "top_promotion_candidates": top_promotions,
        "health_indicators": health,
    }

    return report


def compute_health_indicators(tier_utilization: dict[str, dict],
                              wear_metrics: list[dict],
                              balance_score: float) -> dict[str, Any]:
    """
    Compute overall storage health indicators.

    Health is assessed across three dimensions:
    - Capacity health: are tiers approaching full?
    - Endurance health: are SSDs wearing out?
    - Balance health: are blocks on appropriate tiers?
    """
    # Capacity health: worst-case utilization across tiers
    max_util = 0.0
    for tier_id, util in tier_utilization.items():
        max_util = max(max_util, util["utilization_pct"])

    capacity_health = "critical" if max_util > 90 else \
                      "warning" if max_util > 75 else "healthy"

    # Endurance health: worst-case endurance consumed
    max_endurance = 0.0
    for wear in wear_metrics:
        max_endurance = max(max_endurance,
                          wear.get("endurance_consumed_fraction", 0.0))

    endurance_health = "critical" if max_endurance > 0.8 else \
                       "warning" if max_endurance > 0.5 else "healthy"

    # Balance health: how well-aligned are placements?
    balance_health = "critical" if balance_score < 0.3 else \
                     "warning" if balance_score < 0.7 else "healthy"

    # Overall health: worst of all dimensions
    health_priority = {"critical": 2, "warning": 1, "healthy": 0}
    overall_priority = max(
        health_priority[capacity_health],
        health_priority[endurance_health],
        health_priority[balance_health]
    )
    overall = {0: "healthy", 1: "warning", 2: "critical"}[overall_priority]

    return {
        "overall": overall,
        "capacity": capacity_health,
        "endurance": endurance_health,
        "balance": balance_health,
        "max_utilization_pct": round(max_util, 2),
        "max_endurance_consumed": round(max_endurance, 8),
        "tier_balance_score": balance_score,
    }


def format_wear_metrics(wear_metrics: list[dict]) -> list[dict]:
    """
    Format wear metrics for report output.

    Ensures consistent field ordering and precision.
    """
    formatted = []
    for wear in wear_metrics:
        formatted.append({
            "device_id": wear["device_id"],
            "write_amplification_factor": wear["write_amplification_factor"],
            "endurance_consumed_fraction": wear["endurance_consumed_fraction"],
            "wear_rate_per_second": wear["wear_rate_per_second"],
            "remaining_life_hours": wear["remaining_life_hours"],
        })
    return formatted


def write_report(report: dict[str, Any], output_path: str) -> None:
    """Write the report to JSON file."""
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2, default=str)
