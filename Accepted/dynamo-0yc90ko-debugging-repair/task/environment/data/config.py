"""Configuration for the event processing pipeline."""
import json

SEVERITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}
WINDOW_MINUTES = 60


def load_config(path="/app/config.json"):
    """Load pipeline configuration."""
    return json.load(open(path))


def get_severity_weight(level):
    """Map severity level string to numeric weight."""
    return SEVERITY_WEIGHTS.get(level, 0)


def compute_score(priority, impact, severity_level):
    """Compute composite event score.

    Formula: (priority * impact) + severity_weight
    """
    weight = get_severity_weight(severity_level)
    return int(priority * impact) + weight
