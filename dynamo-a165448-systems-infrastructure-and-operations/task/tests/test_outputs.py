"""
Test suite for the storage tiering engine output verification.

Validates that the pipeline produces correct tiering analysis results
when run on the hidden test configuration.
"""

import json
import pytest


EXPECTED_PATH = "/tests/expected_output.json"
OUTPUT_PATH = "/app/output.json"


@pytest.fixture
def output():
    """Load the pipeline output."""
    with open(OUTPUT_PATH, "r") as f:
        return json.load(f)


@pytest.fixture
def expected():
    """Load the expected output."""
    with open(EXPECTED_PATH, "r") as f:
        return json.load(f)


def test_heat_distribution(output, expected):
    """Verify that block heat classification produces correct hot/warm/cold counts."""
    assert output["heat_distribution"] == expected["heat_distribution"], (
        f"Heat distribution mismatch: got {output['heat_distribution']}, "
        f"expected {expected['heat_distribution']}"
    )


def test_wear_metrics_ssd(output, expected):
    """Verify SSD wear rate estimation uses correct interval write volume."""
    out_ssd = next(w for w in output["wear_metrics"] if w["device_id"] == "ssd_nvme_0")
    exp_ssd = next(w for w in expected["wear_metrics"] if w["device_id"] == "ssd_nvme_0")

    assert abs(out_ssd["wear_rate_per_second"] - exp_ssd["wear_rate_per_second"]) < 1e-10, (
        f"SSD wear rate mismatch: got {out_ssd['wear_rate_per_second']}, "
        f"expected {exp_ssd['wear_rate_per_second']}"
    )
    assert out_ssd["remaining_life_hours"] == exp_ssd["remaining_life_hours"], (
        f"SSD remaining life mismatch: got {out_ssd['remaining_life_hours']}, "
        f"expected {exp_ssd['remaining_life_hours']}"
    )


def test_wear_metrics_hdd(output, expected):
    """Verify HDD wear rate reflects interval-only write activity."""
    out_hdd = next(w for w in output["wear_metrics"] if w["device_id"] == "hdd_sata_0")
    exp_hdd = next(w for w in expected["wear_metrics"] if w["device_id"] == "hdd_sata_0")

    assert abs(out_hdd["wear_rate_per_second"] - exp_hdd["wear_rate_per_second"]) < 1e-10, (
        f"HDD wear rate mismatch: got {out_hdd['wear_rate_per_second']}, "
        f"expected {exp_hdd['wear_rate_per_second']}"
    )


def test_wear_metrics_archive(output, expected):
    """Verify archive device wear estimation consistency."""
    out_arch = next(w for w in output["wear_metrics"] if w["device_id"] == "archive_0")
    exp_arch = next(w for w in expected["wear_metrics"] if w["device_id"] == "archive_0")

    assert abs(out_arch["wear_rate_per_second"] - exp_arch["wear_rate_per_second"]) < 1e-10, (
        f"Archive wear rate mismatch: got {out_arch['wear_rate_per_second']}, "
        f"expected {exp_arch['wear_rate_per_second']}"
    )


def test_migration_plan_summary(output, expected):
    """Verify migration plan produces correct promotion/demotion counts and costs."""
    out_summary = output["migration_plan"]["summary"]
    exp_summary = expected["migration_plan"]["summary"]

    assert out_summary["total_migrations"] == exp_summary["total_migrations"], (
        f"Total migrations mismatch: got {out_summary['total_migrations']}, "
        f"expected {exp_summary['total_migrations']}"
    )
    assert out_summary["promotions"] == exp_summary["promotions"], (
        f"Promotions count mismatch: got {out_summary['promotions']}, "
        f"expected {exp_summary['promotions']}"
    )
    assert out_summary["demotions"] == exp_summary["demotions"], (
        f"Demotions count mismatch: got {out_summary['demotions']}, "
        f"expected {exp_summary['demotions']}"
    )
    assert abs(out_summary["total_iops_cost"] - exp_summary["total_iops_cost"]) < 0.01, (
        f"IOPS cost mismatch: got {out_summary['total_iops_cost']}, "
        f"expected {exp_summary['total_iops_cost']}"
    )


def test_tier_balance_score(output, expected):
    """Verify tier alignment score matches expected value."""
    assert abs(output["tier_balance_score"] - expected["tier_balance_score"]) < 1e-4, (
        f"Tier balance score mismatch: got {output['tier_balance_score']}, "
        f"expected {expected['tier_balance_score']}"
    )


def test_health_indicators(output, expected):
    """Verify overall health assessment and sub-dimension classifications."""
    out_health = output["health_indicators"]
    exp_health = expected["health_indicators"]

    assert out_health["overall"] == exp_health["overall"], (
        f"Overall health mismatch: got {out_health['overall']}, "
        f"expected {exp_health['overall']}"
    )
    assert out_health["capacity"] == exp_health["capacity"], (
        f"Capacity health mismatch: got {out_health['capacity']}, "
        f"expected {exp_health['capacity']}"
    )
    assert out_health["endurance"] == exp_health["endurance"], (
        f"Endurance health mismatch: got {out_health['endurance']}, "
        f"expected {exp_health['endurance']}"
    )
    assert out_health["balance"] == exp_health["balance"], (
        f"Balance health mismatch: got {out_health['balance']}, "
        f"expected {exp_health['balance']}"
    )


def test_tier_utilization(output, expected):
    """Verify per-tier capacity utilization calculations."""
    for tier_id in expected["tier_utilization"]:
        assert tier_id in output["tier_utilization"], (
            f"Missing tier {tier_id} in utilization output"
        )
        out_tier = output["tier_utilization"][tier_id]
        exp_tier = expected["tier_utilization"][tier_id]

        assert abs(out_tier["utilization_pct"] - exp_tier["utilization_pct"]) < 0.01, (
            f"Tier {tier_id} utilization mismatch: got {out_tier['utilization_pct']}, "
            f"expected {exp_tier['utilization_pct']}"
        )


def test_top_promotion_candidates(output, expected):
    """Verify top promotion candidates are correctly scored and ordered."""
    out_top = output["top_promotion_candidates"]
    exp_top = expected["top_promotion_candidates"]

    assert len(out_top) == len(exp_top), (
        f"Promotion candidates count mismatch: got {len(out_top)}, "
        f"expected {len(exp_top)}"
    )

    # Verify top candidate
    if exp_top:
        assert out_top[0]["block_key"] == exp_top[0]["block_key"], (
            f"Top candidate mismatch: got {out_top[0]['block_key']}, "
            f"expected {exp_top[0]['block_key']}"
        )
        assert out_top[0]["decayed_score"] == exp_top[0]["decayed_score"], (
            f"Top candidate score mismatch: got {out_top[0]['decayed_score']}, "
            f"expected {exp_top[0]['decayed_score']}"
        )
