"""Data loader for A/B test experiment configurations and observations."""

import json
import sys
from typing import Any


def load_experiment(filepath: str) -> dict[str, Any]:
    """Load and validate an experiment configuration file.
    
    Expected schema:
    {
        "experiment_id": str,
        "experiment_name": str,
        "metrics": [
            {
                "name": str,
                "type": "continuous" | "proportion",
                "primary": bool,
                "alpha": float,
                "direction": "increase" | "decrease" | "any"
            }
        ],
        "variants": {
            "control": {"observations": [float, ...]},
            "treatment": {"observations": [float, ...]}
        },
        "analysis_config": {
            "confidence_level": float,
            "correction_method": "bonferroni" | "benjamini_hochberg",
            "power_target": float,
            "minimum_detectable_effect": float | null
        }
    }
    """
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading experiment file: {e}", file=sys.stderr)
        sys.exit(1)
    
    _validate_schema(data)
    return data


def _validate_schema(data: dict[str, Any]) -> None:
    """Validate the experiment data against the expected schema."""
    required_top = ["experiment_id", "experiment_name", "metrics", "variants", "analysis_config"]
    for field in required_top:
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    
    if not isinstance(data["metrics"], list) or len(data["metrics"]) == 0:
        raise ValueError("'metrics' must be a non-empty list")
    
    for i, metric in enumerate(data["metrics"]):
        _validate_metric(metric, i)
    
    if "control" not in data["variants"] or "treatment" not in data["variants"]:
        raise ValueError("'variants' must contain 'control' and 'treatment' keys")
    
    for variant_name, variant_data in data["variants"].items():
        if "observations" not in variant_data:
            raise ValueError(f"Variant '{variant_name}' missing 'observations'")
        if not isinstance(variant_data["observations"], list):
            raise ValueError(f"Variant '{variant_name}' observations must be a list")
        if len(variant_data["observations"]) == 0:
            raise ValueError(f"Variant '{variant_name}' has no observations")
    
    _validate_analysis_config(data["analysis_config"])


def _validate_metric(metric: dict, index: int) -> None:
    """Validate a single metric definition."""
    required = ["name", "type", "primary", "alpha", "direction"]
    for field in required:
        if field not in metric:
            raise ValueError(f"Metric {index} missing field: {field}")
    
    if metric["type"] not in ("continuous", "proportion"):
        raise ValueError(f"Metric {index}: type must be 'continuous' or 'proportion'")
    
    if not isinstance(metric["primary"], bool):
        raise ValueError(f"Metric {index}: 'primary' must be boolean")
    
    if not (0 < metric["alpha"] <= 0.5):
        raise ValueError(f"Metric {index}: alpha must be in (0, 0.5]")
    
    if metric["direction"] not in ("increase", "decrease", "any"):
        raise ValueError(f"Metric {index}: direction must be 'increase', 'decrease', or 'any'")


def _validate_analysis_config(config: dict) -> None:
    """Validate analysis configuration parameters."""
    required = ["confidence_level", "correction_method", "power_target"]
    for field in required:
        if field not in config:
            raise ValueError(f"analysis_config missing field: {field}")
    
    if not (0.5 <= config["confidence_level"] < 1.0):
        raise ValueError("confidence_level must be in [0.5, 1.0)")
    
    if config["correction_method"] not in ("bonferroni", "benjamini_hochberg"):
        raise ValueError("correction_method must be 'bonferroni' or 'benjamini_hochberg'")
    
    if not (0 < config["power_target"] < 1.0):
        raise ValueError("power_target must be in (0, 1.0)")


def extract_metric_observations(data: dict, metric_name: str) -> tuple[list[float], list[float]]:
    """Extract control and treatment observations for a specific metric.
    
    If per-metric observations exist (variants.control.per_metric.{name}),
    use those. Otherwise, fall back to the top-level observations.
    """
    control_variant = data["variants"]["control"]
    treatment_variant = data["variants"]["treatment"]
    
    # Check for per-metric observations
    if "per_metric" in control_variant and metric_name in control_variant["per_metric"]:
        control_obs = control_variant["per_metric"][metric_name]
    else:
        control_obs = control_variant["observations"]
    
    if "per_metric" in treatment_variant and metric_name in treatment_variant["per_metric"]:
        treatment_obs = treatment_variant["per_metric"][metric_name]
    else:
        treatment_obs = treatment_variant["observations"]
    
    return control_obs, treatment_obs
