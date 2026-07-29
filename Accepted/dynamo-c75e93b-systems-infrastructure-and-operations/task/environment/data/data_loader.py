"""
Data loader module for the metrics aggregation pipeline.

Loads raw metrics from JSON input files, validates schema structure,
and normalizes timestamps to epoch seconds for downstream processing.
"""

import json
import sys
from typing import Any


REQUIRED_TOP_LEVEL_KEYS = {"metrics", "metadata"}
REQUIRED_METADATA_KEYS = {"collection_interval_sec", "sources", "retention_policy"}
VALID_METRIC_TYPES = {"counter", "gauge", "histogram"}
REQUIRED_METRIC_KEYS = {"name", "type", "source", "datapoints"}
REQUIRED_DATAPOINT_KEYS = {"timestamp", "value"}
REQUIRED_HISTOGRAM_KEYS = {"timestamp", "buckets"}


def load_metrics_file(filepath: str) -> dict:
    """Load and parse a JSON metrics file from disk."""
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"Error: metrics file not found: {filepath}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: invalid JSON in {filepath}: {e}", file=sys.stderr)
        sys.exit(1)
    return data


def validate_schema(data: dict) -> list[str]:
    """
    Validate the top-level schema of a metrics payload.
    Returns a list of validation error messages (empty if valid).
    """
    errors = []

    missing_top = REQUIRED_TOP_LEVEL_KEYS - set(data.keys())
    if missing_top:
        errors.append(f"Missing top-level keys: {sorted(missing_top)}")
        return errors

    metadata = data["metadata"]
    missing_meta = REQUIRED_METADATA_KEYS - set(metadata.keys())
    if missing_meta:
        errors.append(f"Missing metadata keys: {sorted(missing_meta)}")

    if not isinstance(data["metrics"], list):
        errors.append("'metrics' must be a list")
        return errors

    for i, metric in enumerate(data["metrics"]):
        metric_errors = _validate_metric(metric, i)
        errors.extend(metric_errors)

    return errors


def _validate_metric(metric: dict, index: int) -> list[str]:
    """Validate a single metric entry."""
    errors = []
    prefix = f"metrics[{index}]"

    if not isinstance(metric, dict):
        errors.append(f"{prefix}: must be a dictionary")
        return errors

    missing_keys = REQUIRED_METRIC_KEYS - set(metric.keys())
    if missing_keys:
        errors.append(f"{prefix}: missing keys {sorted(missing_keys)}")
        return errors

    if metric["type"] not in VALID_METRIC_TYPES:
        errors.append(f"{prefix}: invalid type '{metric['type']}' "
                      f"(must be one of {sorted(VALID_METRIC_TYPES)})")

    if not isinstance(metric["datapoints"], list):
        errors.append(f"{prefix}: 'datapoints' must be a list")
        return errors

    if len(metric["datapoints"]) == 0:
        errors.append(f"{prefix}: 'datapoints' must not be empty")
        return errors

    for j, dp in enumerate(metric["datapoints"]):
        dp_errors = _validate_datapoint(dp, metric["type"], f"{prefix}.datapoints[{j}]")
        errors.extend(dp_errors)

    return errors


def _validate_datapoint(dp: dict, metric_type: str, prefix: str) -> list[str]:
    """Validate a single datapoint based on metric type."""
    errors = []

    if not isinstance(dp, dict):
        errors.append(f"{prefix}: must be a dictionary")
        return errors

    if metric_type == "histogram":
        missing = REQUIRED_HISTOGRAM_KEYS - set(dp.keys())
        if missing:
            errors.append(f"{prefix}: missing keys {sorted(missing)}")
        elif not isinstance(dp["buckets"], dict):
            errors.append(f"{prefix}: 'buckets' must be a dictionary")
        elif len(dp["buckets"]) == 0:
            errors.append(f"{prefix}: 'buckets' must not be empty")
    else:
        missing = REQUIRED_DATAPOINT_KEYS - set(dp.keys())
        if missing:
            errors.append(f"{prefix}: missing keys {sorted(missing)}")
        elif not isinstance(dp["value"], (int, float)):
            errors.append(f"{prefix}: 'value' must be numeric")

    if "timestamp" in dp and not isinstance(dp["timestamp"], (int, float)):
        errors.append(f"{prefix}: 'timestamp' must be numeric")

    return errors


def extract_metrics_by_type(data: dict) -> dict[str, list[dict]]:
    """
    Group metrics by their type (counter, gauge, histogram).
    Returns a dict mapping type name to list of metric entries.
    """
    grouped: dict[str, list[dict]] = {t: [] for t in VALID_METRIC_TYPES}

    for metric in data["metrics"]:
        mtype = metric["type"]
        if mtype in grouped:
            grouped[mtype].append(metric)

    return grouped


def get_collection_interval(data: dict) -> float:
    """Extract the collection interval from metadata."""
    return float(data["metadata"]["collection_interval_sec"])


def get_sources(data: dict) -> list[str]:
    """Extract the list of sources from metadata."""
    return list(data["metadata"]["sources"])


def get_retention_policy(data: dict) -> dict:
    """Extract retention policy configuration."""
    return data["metadata"]["retention_policy"]


def sort_datapoints_by_timestamp(metric: dict) -> list[dict]:
    """Return datapoints sorted by timestamp (ascending)."""
    return sorted(metric["datapoints"], key=lambda dp: dp["timestamp"])
