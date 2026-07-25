"""
Event loader and validation module.
"""

import json
import os


def load_events(filepath):
    """Load event stream from JSON file."""
    with open(filepath, "r") as f:
        return json.load(f)


def validate_stream(config):
    """Validate event stream configuration."""
    errors = []
    required = ["stream_name", "events", "window_config", "processing_config"]
    for key in required:
        if key not in config:
            errors.append(f"Missing: {key}")
    if errors:
        return {"valid": False, "errors": errors}

    if "window_size_sec" not in config["window_config"]:
        errors.append("Missing window_config.window_size_sec")
    if "decay_factor" not in config["processing_config"]:
        errors.append("Missing processing_config.decay_factor")

    events = config.get("events", [])
    if not events:
        errors.append("Empty event list")
    for i, e in enumerate(events):
        if "timestamp" not in e or "value" not in e or "key" not in e:
            errors.append(f"Event {i}: missing required fields")
            break

    return {"valid": len(errors) == 0, "errors": errors}
