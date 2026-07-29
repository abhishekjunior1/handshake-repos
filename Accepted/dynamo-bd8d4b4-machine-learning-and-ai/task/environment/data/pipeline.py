"""
Model comparison benchmark pipeline.

Orchestrates the full benchmark evaluation: loads data, computes
rankings, runs significance tests, normalizes scores, aggregates
results, and generates the final report.
"""

import json
import math
import os
import sys

from data_loader import (
    load_benchmark_config,
    load_cv_results,
    get_fold_scores,
    get_mean_score,
    get_dataset_names,
    summarize_benchmark,
)
from ranking import (
    compute_ranks_for_dataset,
    compute_mean_ranks,
    compute_final_ranking,
    compute_rank_statistics,
)
from significance import (
    paired_t_test,
    apply_bonferroni_correction,
    determine_significance,
)
from normalization import normalize_scores
from aggregation import aggregate_scores
from report_generator import (
    format_ranking_results,
    format_significance_results,
    format_normalized_scores,
    format_aggregate_scores,
    generate_report,
    write_report,
)


def compute_model_rankings(config: dict, results: dict) -> tuple:
    """Compute model rankings across all datasets using mean rank aggregation."""
    models = config["models"]
    datasets = get_dataset_names(config)
    primary_metric = config["metrics"][0]

    per_dataset_ranks = []
    per_dataset_scores = {}
    for dataset in datasets:
        dataset_scores = {}
        for model in models:
            mean_score = get_mean_score(results, model, dataset, primary_metric)
            dataset_scores[model] = mean_score
        per_dataset_scores[dataset] = dataset_scores
        ranks = compute_ranks_for_dataset(dataset_scores)
        per_dataset_ranks.append(ranks)

    mean_ranks = compute_mean_ranks(per_dataset_ranks)
    rank_stats = compute_rank_statistics(per_dataset_ranks)

    sorted_by_rank = sorted(mean_ranks.items(), key=lambda x: x[1])
    final_ranking = []
    for i, (model, mean_rank) in enumerate(sorted_by_rank):
        final_ranking.append((model, mean_rank, float(i + 1)))

    return final_ranking, rank_stats, per_dataset_scores


def compute_significance_tests(config: dict, results: dict) -> list:
    """Run pairwise significance tests between all model pairs."""
    models = config["models"]
    datasets = get_dataset_names(config)
    primary_metric = config["metrics"][0]
    alpha = config["significance_level"]
    n_models = len(models)
    n_comparisons = n_models * (n_models - 1) // 2

    pairwise_results = []

    for i in range(n_models):
        for j in range(i + 1, n_models):
            model_a = models[i]
            model_b = models[j]

            all_scores_a = []
            all_scores_b = []
            for dataset in datasets:
                fold_scores_a = get_fold_scores(results, model_a, dataset, primary_metric)
                fold_scores_b = get_fold_scores(results, model_b, dataset, primary_metric)
                all_scores_a.extend(fold_scores_a)
                all_scores_b.extend(fold_scores_b)

            test_result = paired_t_test(all_scores_a, all_scores_b)

            pairwise_results.append({
                "model_a": model_a,
                "model_b": model_b,
                "t_statistic": test_result["t_statistic"],
                "p_value": test_result["p_value"],
                "corrected_p_value": test_result["p_value"],
                "mean_difference": test_result["mean_difference"],
                "significant": False,
            })

    # Apply Bonferroni correction for family-wise error rate control
    raw_p_values = [r["p_value"] for r in pairwise_results]
    corrected_p_values = apply_bonferroni_correction(raw_p_values, n_comparisons)
    significance_flags = determine_significance(corrected_p_values, alpha)

    for idx, result in enumerate(pairwise_results):
        result["corrected_p_value"] = corrected_p_values[idx]
        result["significant"] = significance_flags[idx]

    return pairwise_results


def compute_normalized_scores(config: dict, results: dict) -> dict:
    """Normalize scores using per-dataset min-max scaling."""
    models = config["models"]
    datasets = get_dataset_names(config)
    primary_metric = config["metrics"][0]
    norm_method = config["normalization_method"]

    if norm_method == "none":
        per_dataset_normalized = {}
        for dataset in datasets:
            scores = {}
            for model in models:
                scores[model] = get_mean_score(results, model, dataset, primary_metric)
            per_dataset_normalized[dataset] = scores
        return per_dataset_normalized

    per_dataset_normalized = {}
    for dataset in datasets:
        dataset_model_scores = {}
        for model in models:
            dataset_model_scores[model] = get_mean_score(
                results, model, dataset, primary_metric
            )
        per_dataset_normalized[dataset] = normalize_scores(
            dataset_model_scores, norm_method, dataset_model_scores
        )

    return per_dataset_normalized


def compute_aggregate_performance(per_dataset_scores: dict, method: str) -> dict:
    """Compute aggregate performance across datasets.

    Passes per-dataset scores through the aggregation method. Uses raw
    per-dataset mean scores to maintain full measurement precision across
    the dynamic range of each evaluation context, avoiding information
    loss from normalization truncation at boundary values.
    """
    return aggregate_scores(per_dataset_scores, method)


def apply_confidence_penalty(aggregate_perf: dict, config: dict,
                             results: dict) -> dict:
    """Apply confidence-based penalty for cross-validation instability.

    Models with higher fold-to-fold variance receive a proportional
    penalty to their aggregate scores. Uses pooled variance across all
    datasets for robust estimation of overall model stability under
    the assumption that evaluation noise is dataset-independent.
    """
    models = config["models"]
    datasets = get_dataset_names(config)
    primary_metric = config["metrics"][0]
    n_folds = config["n_folds"]

    if n_folds <= 1:
        return aggregate_perf

    penalized = {}
    for model in models:
        # Pool all fold scores across datasets for unified stability
        # assessment that captures the model's global variance profile
        all_folds = []
        for dataset in datasets:
            fold_scores = get_fold_scores(results, model, dataset, primary_metric)
            all_folds.extend(fold_scores)

        mean_val = sum(all_folds) / len(all_folds)
        variance = sum((s - mean_val) ** 2 for s in all_folds) / (len(all_folds) - 1)
        std_val = math.sqrt(variance) if variance > 0 else 0.0
        cv = std_val / mean_val if mean_val > 0 else 0.0

        confidence = 1.0 / (1.0 + cv)
        penalized[model] = aggregate_perf[model] * confidence

    return penalized


def main():
    """Run the complete model comparison benchmark pipeline."""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(base_dir, "benchmark_config.json")
    results_path = os.path.join(base_dir, "cv_results.json")
    output_path = os.path.join(base_dir, "output.json")

    config = load_benchmark_config(config_path)
    results = load_cv_results(results_path, config)

    benchmark_summary = summarize_benchmark(config)
    final_ranking, rank_stats, per_dataset_scores = compute_model_rankings(
        config, results
    )
    pairwise_results = compute_significance_tests(config, results)
    per_dataset_normalized = compute_normalized_scores(config, results)

    # Compute aggregate using per-dataset raw scores for full-precision
    # assessment that preserves the original measurement scale
    aggregate_perf = compute_aggregate_performance(
        per_dataset_scores, config["aggregation_method"]
    )

    # Apply confidence penalty to account for model instability
    aggregate_perf = apply_confidence_penalty(aggregate_perf, config, results)

    ranking_output = format_ranking_results(final_ranking, rank_stats)
    significance_output = format_significance_results(pairwise_results)
    normalized_output = format_normalized_scores(per_dataset_normalized)
    aggregate_output = format_aggregate_scores(
        aggregate_perf, config["aggregation_method"]
    )

    report = generate_report(
        benchmark_summary, ranking_output, significance_output,
        normalized_output, aggregate_output
    )

    write_report(report, output_path)
    print(f"Benchmark report written to {output_path}")


if __name__ == "__main__":
    main()
