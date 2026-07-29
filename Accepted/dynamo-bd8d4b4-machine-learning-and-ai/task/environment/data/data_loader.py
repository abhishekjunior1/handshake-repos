"""
Data loader for model comparison benchmark pipeline.

Loads benchmark configuration and cross-validation results from JSON files.
Validates schema, handles missing fields, and returns structured data
for downstream processing.
"""

import json
import os
import sys
from typing import Any


def load_benchmark_config(config_path: str) -> dict:
    """Load and validate benchmark configuration file.

    Expected schema:
    {
        "benchmark_name": str,
        "models": [str, ...],
        "datasets": [{"name": str, "n_samples": int, "n_classes": int}, ...],
        "n_folds": int,
        "metrics": [str, ...],
        "significance_level": float,
        "normalization_method": str,
        "aggregation_method": str
    }
    """
    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found: {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, "r") as f:
        config = json.load(f)

    required_fields = [
        "benchmark_name", "models", "datasets", "n_folds",
        "metrics", "significance_level", "normalization_method",
        "aggregation_method"
    ]

    for field in required_fields:
        if field not in config:
            print(f"Error: Missing required field '{field}' in config", file=sys.stderr)
            sys.exit(1)

    if not isinstance(config["models"], list) or len(config["models"]) < 2:
        print("Error: At least 2 models required for comparison", file=sys.stderr)
        sys.exit(1)

    if not isinstance(config["datasets"], list) or len(config["datasets"]) < 1:
        print("Error: At least 1 dataset required", file=sys.stderr)
        sys.exit(1)

    for dataset in config["datasets"]:
        if not all(k in dataset for k in ["name", "n_samples", "n_classes"]):
            print(f"Error: Dataset missing required fields: {dataset}", file=sys.stderr)
            sys.exit(1)

    if config["n_folds"] < 1:
        print("Error: n_folds must be >= 1", file=sys.stderr)
        sys.exit(1)

    if not (0.0 < config["significance_level"] < 1.0):
        print("Error: significance_level must be in (0, 1)", file=sys.stderr)
        sys.exit(1)

    valid_norms = ["min_max", "z_score", "none"]
    if config["normalization_method"] not in valid_norms:
        print(f"Error: normalization_method must be one of {valid_norms}", file=sys.stderr)
        sys.exit(1)

    valid_aggs = ["arithmetic_mean", "geometric_mean"]
    if config["aggregation_method"] not in valid_aggs:
        print(f"Error: aggregation_method must be one of {valid_aggs}", file=sys.stderr)
        sys.exit(1)

    return config


def load_cv_results(results_path: str, config: dict) -> dict:
    """Load cross-validation results for all models on all datasets.

    Expected schema:
    {
        "results": {
            "<model_name>": {
                "<dataset_name>": {
                    "<metric_name>": [float, ...],  # one score per fold
                    ...
                },
                ...
            },
            ...
        }
    }

    Returns validated results dict with structure:
    results[model][dataset][metric] = [fold_scores]
    """
    if not os.path.exists(results_path):
        print(f"Error: Results file not found: {results_path}", file=sys.stderr)
        sys.exit(1)

    with open(results_path, "r") as f:
        data = json.load(f)

    if "results" not in data:
        print("Error: Results file must have 'results' key", file=sys.stderr)
        sys.exit(1)

    results = data["results"]
    models = config["models"]
    datasets = [d["name"] for d in config["datasets"]]
    metrics = config["metrics"]
    n_folds = config["n_folds"]

    for model in models:
        if model not in results:
            print(f"Error: Missing results for model '{model}'", file=sys.stderr)
            sys.exit(1)

        for dataset in datasets:
            if dataset not in results[model]:
                print(f"Error: Missing results for model '{model}' on dataset '{dataset}'",
                      file=sys.stderr)
                sys.exit(1)

            for metric in metrics:
                if metric not in results[model][dataset]:
                    print(f"Error: Missing metric '{metric}' for model '{model}' "
                          f"on dataset '{dataset}'", file=sys.stderr)
                    sys.exit(1)

                scores = results[model][dataset][metric]
                if not isinstance(scores, list) or len(scores) != n_folds:
                    print(f"Error: Expected {n_folds} fold scores for "
                          f"{model}/{dataset}/{metric}, got {len(scores) if isinstance(scores, list) else 'non-list'}",
                          file=sys.stderr)
                    sys.exit(1)

                for i, score in enumerate(scores):
                    if not isinstance(score, (int, float)):
                        print(f"Error: Non-numeric score at fold {i} for "
                              f"{model}/{dataset}/{metric}", file=sys.stderr)
                        sys.exit(1)

    return results


def get_fold_scores(results: dict, model: str, dataset: str, metric: str) -> list:
    """Extract fold scores for a specific model/dataset/metric combination."""
    return results[model][dataset][metric]


def get_mean_score(results: dict, model: str, dataset: str, metric: str) -> float:
    """Compute mean score across folds for a model/dataset/metric."""
    scores = get_fold_scores(results, model, dataset, metric)
    return sum(scores) / len(scores)


def get_dataset_names(config: dict) -> list:
    """Return list of dataset names from config."""
    return [d["name"] for d in config["datasets"]]


def get_dataset_info(config: dict, dataset_name: str) -> dict:
    """Get full dataset info dict by name."""
    for d in config["datasets"]:
        if d["name"] == dataset_name:
            return d
    return {}


def summarize_benchmark(config: dict) -> dict:
    """Create a summary of benchmark parameters."""
    return {
        "name": config["benchmark_name"],
        "n_models": len(config["models"]),
        "n_datasets": len(config["datasets"]),
        "n_folds": config["n_folds"],
        "n_metrics": len(config["metrics"]),
        "total_evaluations": (
            len(config["models"]) *
            len(config["datasets"]) *
            config["n_folds"] *
            len(config["metrics"])
        )
    }
