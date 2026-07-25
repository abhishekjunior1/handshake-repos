"""
Report generator for model comparison benchmark.

Formats benchmark results into the final output JSON structure.
Combines rankings, significance tests, normalized scores, and
aggregate results into a comprehensive benchmark report.
"""

import json
from typing import Any


def format_ranking_results(final_ranking: list, rank_stats: dict) -> dict:
    """Format ranking results for output.

    Args:
        final_ranking: list of (model, mean_rank, position) tuples
        rank_stats: per-model rank statistics dict

    Returns:
        dict with model rankings and statistics
    """
    rankings = []
    for model, mean_rank, position in final_ranking:
        entry = {
            "model": model,
            "mean_rank": round(mean_rank, 6),
            "position": position,
        }
        if model in rank_stats:
            entry["std_rank"] = round(rank_stats[model]["std_rank"], 6)
            entry["best_rank"] = rank_stats[model]["min_rank"]
            entry["worst_rank"] = rank_stats[model]["max_rank"]
        rankings.append(entry)

    return {"rankings": rankings}


def format_significance_results(pairwise_results: list) -> dict:
    """Format pairwise significance test results for output.

    Args:
        pairwise_results: list of dicts with model_a, model_b,
                         t_statistic, p_value, corrected_p_value,
                         significant, mean_difference

    Returns:
        dict with pairwise comparisons
    """
    comparisons = []
    for result in pairwise_results:
        entry = {
            "model_a": result["model_a"],
            "model_b": result["model_b"],
            "t_statistic": round(result["t_statistic"], 6),
            "p_value": round(result["p_value"], 6),
            "corrected_p_value": round(result["corrected_p_value"], 6),
            "significant": result["significant"],
            "mean_difference": round(result["mean_difference"], 6)
        }
        comparisons.append(entry)

    n_significant = sum(1 for c in comparisons if c["significant"])
    n_total = len(comparisons)

    return {
        "pairwise_comparisons": comparisons,
        "n_significant": n_significant,
        "n_total": n_total
    }


def format_normalized_scores(per_dataset_normalized: dict) -> dict:
    """Format normalized scores for output.

    Args:
        per_dataset_normalized: dict mapping dataset -> {model: normalized_score}

    Returns:
        dict with per-dataset normalized scores
    """
    formatted = {}
    for dataset, scores in per_dataset_normalized.items():
        formatted[dataset] = {
            model: round(score, 6) for model, score in scores.items()
        }
    return {"normalized_scores": formatted}


def format_aggregate_scores(aggregate_scores: dict, method: str) -> dict:
    """Format aggregate scores for output.

    Args:
        aggregate_scores: dict mapping model -> aggregate score
        method: aggregation method used

    Returns:
        dict with aggregate scores and method info
    """
    scores_list = sorted(
        aggregate_scores.items(),
        key=lambda x: x[1],
        reverse=True
    )

    return {
        "aggregate_scores": {
            model: round(score, 6) for model, score in scores_list
        },
        "aggregation_method": method
    }


def generate_report(benchmark_summary: dict, ranking_results: dict,
                    significance_results: dict, normalized_results: dict,
                    aggregate_results: dict) -> dict:
    """Assemble the complete benchmark report.

    Args:
        benchmark_summary: benchmark configuration summary
        ranking_results: formatted ranking output
        significance_results: formatted significance output
        normalized_results: formatted normalization output
        aggregate_results: formatted aggregate output

    Returns:
        Complete benchmark report dict
    """
    report = {
        "benchmark_summary": benchmark_summary,
        "model_rankings": ranking_results,
        "statistical_significance": significance_results,
        "score_normalization": normalized_results,
        "aggregate_performance": aggregate_results
    }

    return report


def write_report(report: dict, output_path: str) -> None:
    """Write benchmark report to JSON file.

    Args:
        report: complete benchmark report dict
        output_path: path to write output JSON
    """
    with open(output_path, "w") as f:
        json.dump(report, f, indent=2)


def validate_report_schema(report: dict) -> list:
    """Validate that report has all required sections.

    Returns list of missing or invalid sections.
    """
    required_sections = [
        "benchmark_summary",
        "model_rankings",
        "statistical_significance",
        "score_normalization",
        "aggregate_performance"
    ]

    errors = []
    for section in required_sections:
        if section not in report:
            errors.append(f"Missing section: {section}")

    if "model_rankings" in report:
        if "rankings" not in report["model_rankings"]:
            errors.append("model_rankings missing 'rankings' key")

    if "statistical_significance" in report:
        if "pairwise_comparisons" not in report["statistical_significance"]:
            errors.append("statistical_significance missing 'pairwise_comparisons' key")

    if "aggregate_performance" in report:
        if "aggregate_scores" not in report["aggregate_performance"]:
            errors.append("aggregate_performance missing 'aggregate_scores' key")

    return errors
