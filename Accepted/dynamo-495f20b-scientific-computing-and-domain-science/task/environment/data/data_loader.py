"""
Data loader for hierarchical Bayesian model fitting.
Loads grouped observation data from JSON, validates structure,
and prepares data arrays for downstream estimation.
"""

import json
import math
from typing import Any


def load_observations(filepath: str) -> dict:
    """Load grouped observation data from a JSON file.

    Expected format:
    {
        "groups": [{"id": str, "observations": [float, ...], ...}, ...],
        "model_config": {...}
    }
    """
    with open(filepath, "r") as f:
        raw = json.load(f)

    groups = _parse_groups(raw.get("groups", []))
    config = _parse_config(raw.get("model_config", {}))

    return {
        "groups": groups,
        "model_config": config,
        "n_groups": len(groups),
        "total_observations": sum(g["n"] for g in groups),
    }


def _parse_groups(group_list: list) -> list:
    """Parse and validate group definitions."""
    groups = []
    for g in group_list:
        obs = g.get("observations", [])
        parsed = {
            "id": g["id"],
            "observations": [float(x) for x in obs],
            "n": len(obs),
            "metadata": g.get("metadata", {}),
        }
        if parsed["n"] < 2:
            raise ValueError(f"Group {g['id']} has fewer than 2 observations")
        groups.append(parsed)
    return groups


def _parse_config(config: dict) -> dict:
    """Parse model configuration parameters."""
    return {
        "prior_mean": config.get("prior_mean", 0.0),
        "prior_variance": config.get("prior_variance", 1e6),
        "credible_level": config.get("credible_level", 0.95),
        "estimation_method": config.get("estimation_method", "empirical_bayes"),
        "shrinkage_type": config.get("shrinkage_type", "james_stein"),
        "interval_method": config.get("interval_method", "posterior_t"),
        "model_comparison": config.get("model_comparison", ["DIC", "WAIC"]),
    }




def compute_grand_mean(data: dict) -> float:
    """Compute the overall grand mean across all observations."""
    total = 0.0
    count = 0
    for group in data["groups"]:
        for obs in group["observations"]:
            total += obs
            count += 1
    return total / count if count > 0 else 0.0


def validate_data_integrity(data: dict) -> dict:
    """Run integrity checks on loaded data."""
    issues = []
    if data["n_groups"] < 2:
        issues.append("Need at least 2 groups for hierarchical modeling")
    for group in data["groups"]:
        if any(math.isnan(x) or math.isinf(x) for x in group["observations"]):
            issues.append(f"Group {group['id']} contains NaN or Inf values")
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "n_groups": data["n_groups"],
        "total_n": data["total_observations"],
    }
