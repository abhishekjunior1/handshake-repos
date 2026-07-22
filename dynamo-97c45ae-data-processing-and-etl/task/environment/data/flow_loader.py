"""
Flow loader and validation module.

Loads NetFlow/sFlow records from JSON files and validates the stream
configuration schema before processing.
"""

import json
import os


def load_flows(filepath):
    """
    Load flow stream configuration from a JSON file.

    Parameters
    ----------
    filepath : str
        Path to the JSON file containing flow data.

    Returns
    -------
    dict
        Parsed flow stream configuration.

    Raises
    ------
    SystemExit
        If the file does not exist or cannot be parsed.
    """
    if not os.path.exists(filepath):
        raise SystemExit(f"Input file not found: {filepath}")

    with open(filepath, "r") as f:
        try:
            config = json.load(f)
        except json.JSONDecodeError as e:
            raise SystemExit(f"Invalid JSON in {filepath}: {e}")

    return config


def validate_stream(config):
    """
    Validate flow stream configuration schema.

    Checks for required top-level keys, nested configuration fields,
    and per-flow record schema compliance.

    Parameters
    ----------
    config : dict
        Parsed flow stream configuration.

    Returns
    -------
    dict
        Validation result with 'valid' boolean and 'errors' list.
    """
    errors = []

    # Check top-level required keys
    required_keys = ["stream_name", "flows", "bin_config", "processing_config"]
    for key in required_keys:
        if key not in config:
            errors.append(f"Missing required key: {key}")

    if errors:
        return {"valid": False, "errors": errors}

    # Check bin_config
    if "bin_duration_sec" not in config["bin_config"]:
        errors.append("Missing bin_config.bin_duration_sec")
    elif config["bin_config"]["bin_duration_sec"] <= 0:
        errors.append("bin_duration_sec must be positive")

    # Check processing_config
    if "smoothing_alpha" not in config["processing_config"]:
        errors.append("Missing processing_config.smoothing_alpha")
    elif not (0 < config["processing_config"]["smoothing_alpha"] <= 1):
        errors.append("smoothing_alpha must be in (0, 1]")

    # Check flows
    flows = config.get("flows", [])
    if not flows:
        errors.append("Empty flow list")

    # Validate individual flow records
    required_flow_fields = ["timestamp", "bytes", "dst_prefix", "flow_id", "collector"]
    for i, flow in enumerate(flows):
        missing = [f for f in required_flow_fields if f not in flow]
        if missing:
            errors.append(f"Flow {i}: missing fields {missing}")
            break
        if flow["bytes"] < 0:
            errors.append(f"Flow {i}: negative byte count")
            break

    return {"valid": len(errors) == 0, "errors": errors}
