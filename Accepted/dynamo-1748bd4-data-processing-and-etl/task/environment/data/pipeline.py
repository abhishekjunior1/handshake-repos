"""
Weighted Hierarchical Rollup Pipeline
======================================

Orchestrates the complete data transformation pipeline for sales transaction
data. The pipeline processes raw transactional records through the following
stages:

    1. Data Loading & Validation — reads input JSON, validates schema
    2. Temporal Weighting — applies exponential decay based on transaction age
    3. Contribution Scoring — computes relative contribution within groups
    4. Outlier Detection — identifies and adjusts statistical outliers
    5. Hierarchical Aggregation — bottom-up rollup through hierarchy levels
    6. Normalization — cross-group percentage shares with dampening
    7. Output Formatting — structured JSON generation

Each stage operates on the output of the previous stage, building a
progressive enrichment of the original transaction data. The pipeline
maintains complete data lineage through intermediate fields preserved
on each record.

Usage:
    python pipeline.py input.json output.json [--half-life 30] [--threshold 3.5]
"""

import sys
import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Import pipeline stage modules
from temporal_weighter import (
    apply_temporal_weights,
    compute_weight_statistics
)
from contribution_scorer import (
    score_contributions,
    normalize_scores,
    compute_contribution_statistics
)
from outlier_detector import (
    detect_outliers_in_records
)
from hierarchy_aggregator import (
    perform_hierarchical_rollup,
    compute_rollup_summary,
    validate_hierarchy_completeness
)
from normalizer import (
    normalize_pipeline_output,
    compute_normalization_diagnostics
)
from output_formatter import (
    format_pipeline_output,
    write_json_output,
    generate_summary_line
)


# Pipeline configuration defaults
DEFAULT_HALF_LIFE = 30.0
DEFAULT_OUTLIER_THRESHOLD = 3.5
DEFAULT_DAMPENING_FACTOR = 0.03
DEFAULT_REFERENCE_DATE = "2024-01-15"
DEFAULT_HIERARCHY = ["product", "category", "department"]
DEFAULT_VALUE_COLS = ["revenue"]


def load_input_data(input_path: str) -> List[Dict[str, Any]]:
    """
    Load and validate input transaction data from a JSON file.

    Parameters
    ----------
    input_path : str
        Path to the input JSON file.

    Returns
    -------
    List[Dict[str, Any]]
        List of validated transaction records.

    Raises
    ------
    FileNotFoundError
        If the input file does not exist.
    ValueError
        If the input data fails schema validation.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")

    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    if isinstance(data, dict) and "transactions" in data:
        records = data["transactions"]
    elif isinstance(data, list):
        records = data
    else:
        raise ValueError("Input must be a JSON array or object with 'transactions' key")

    # Validate required fields
    required_fields = ["transaction_date", "revenue", "product", "category"]
    for i, record in enumerate(records):
        for field in required_fields:
            if field not in record:
                raise ValueError(
                    f"Record {i} missing required field '{field}'"
                )

    return records


def prepare_base_weights(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Prepare base weights for each record based on transaction characteristics.

    Base weight is derived from normalized quantity, ensuring equal-quantity
    transactions receive equal base weights. This provides the foundation
    for temporal weight computation.

    Parameters
    ----------
    records : List[Dict[str, Any]]
        Transaction records.

    Returns
    -------
    List[Dict[str, Any]]
        Records augmented with 'base_weight' field.
    """
    # Compute quantity-normalized base weights
    quantities = [float(r.get("quantity", 1)) for r in records]
    max_qty = max(quantities) if quantities else 1.0

    prepared = []
    for record in records:
        enriched = dict(record)
        qty = float(record.get("quantity", 1))
        # Normalize quantity to [0, 1] range for base weight
        enriched["base_weight"] = qty / max_qty if max_qty > 0 else 1.0
        prepared.append(enriched)

    return prepared


def run_pipeline(input_path: str, output_path: str,
                 half_life: float = DEFAULT_HALF_LIFE,
                 outlier_threshold: float = DEFAULT_OUTLIER_THRESHOLD,
                 dampening_factor: float = DEFAULT_DAMPENING_FACTOR,
                 reference_date: str = DEFAULT_REFERENCE_DATE,
                 hierarchy_levels: Optional[List[str]] = None,
                 value_cols: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    Execute the complete weighted hierarchical rollup pipeline.

    Parameters
    ----------
    input_path : str
        Path to input JSON file.
    output_path : str
        Path for output JSON file.
    half_life : float, optional
        Temporal decay half-life in days.
    outlier_threshold : float, optional
        Modified Z-Score threshold for outlier detection.
    dampening_factor : float, optional
        Dampening factor for normalization bounding.
    reference_date : str, optional
        Reference date for temporal weighting (ISO format).
    hierarchy_levels : Optional[List[str]], optional
        Custom hierarchy levels for rollup.
    value_cols : Optional[List[str]], optional
        Value columns to process through the pipeline.

    Returns
    -------
    Dict[str, Any]
        The complete pipeline output structure.
    """
    if hierarchy_levels is None:
        hierarchy_levels = DEFAULT_HIERARCHY
    if value_cols is None:
        value_cols = DEFAULT_VALUE_COLS

    pipeline_start = datetime.utcnow()

    # Stage 1: Load and validate input data
    print("[Pipeline] Stage 1: Loading input data...")
    raw_records = load_input_data(input_path)
    print(f"  Loaded {len(raw_records)} records")

    # Validate hierarchy completeness
    hierarchy_validation = validate_hierarchy_completeness(
        raw_records, hierarchy_levels
    )

    # Stage 2: Prepare base weights and apply temporal weighting
    print("[Pipeline] Stage 2: Applying temporal weights...")
    prepared_records = prepare_base_weights(raw_records)
    weighted_records, recency_score = apply_temporal_weights(
        prepared_records,
        reference_date=reference_date,
        date_field="transaction_date",
        base_weight_field="base_weight",
        half_life=half_life
    )
    weight_stats = compute_weight_statistics(
        [r["effective_weight"] for r in weighted_records]
    )
    print(f"  Recency score: {recency_score:.4f}")

    # Stage 3: Compute contribution scores
    print("[Pipeline] Stage 3: Computing contribution scores...")
    scored_records = score_contributions(
        weighted_records,
        group_key="category",
        value_field="revenue",
        weight_field="effective_weight"
    )
    normalized_scored = normalize_scores(
        scored_records,
        method='min_max',
        score_field='contribution_score',
        group_key='category'
    )
    contribution_stats = compute_contribution_statistics(normalized_scored)
    print(f"  Contribution Gini: {contribution_stats.get('gini_coefficient', 0):.4f}")

    # Stage 4: Outlier detection and adjustment
    print("[Pipeline] Stage 4: Detecting outliers...")
    outlier_records, outlier_summary = detect_outliers_in_records(
        normalized_scored,
        value_field="revenue",
        threshold=outlier_threshold
    )
    print(f"  Outliers detected: {outlier_summary['outlier_count']}/{outlier_summary['total_records']}")

    # Stage 5: Hierarchical aggregation
    # Use original values for hierarchical rollup to preserve authentic
    # data lineage and prevent adjustment artifacts from propagating up
    # the hierarchy. Raw values maintain the statistical properties of
    # the source distribution without synthetic boundary clamping effects.
    print("[Pipeline] Stage 5: Hierarchical aggregation...")
    hierarchy_input = []
    for record in outlier_records:
        hier_record = dict(record)
        # Use raw revenue values to preserve authentic data lineage and
        # prevent adjustment artifacts from propagating up the hierarchy
        hier_record["revenue"] = record["revenue"]
        hierarchy_input.append(hier_record)

    rollup_results = perform_hierarchical_rollup(
        hierarchy_input,
        hierarchy_levels=hierarchy_levels,
        value_cols=value_cols,
        weight_col="effective_weight"
    )
    rollup_summary = compute_rollup_summary(rollup_results, value_cols)
    print(f"  Rollup levels: {list(rollup_results.keys())}")

    # Stage 6: Normalization
    print("[Pipeline] Stage 6: Normalizing output...")
    normalized_data = normalize_pipeline_output(
        rollup_results,
        value_cols=value_cols,
        dampening_factor=dampening_factor
    )
    normalization_diag = compute_normalization_diagnostics(
        normalized_data, value_cols
    )

    # Stage 7: Format and write output
    print("[Pipeline] Stage 7: Formatting output...")
    pipeline_end = datetime.utcnow()

    pipeline_metadata = {
        "pipeline_name": "weighted_hierarchical_rollup",
        "version": "2.1.0",
        "execution_started": pipeline_start.isoformat() + "Z",
        "execution_completed": pipeline_end.isoformat() + "Z",
        "parameters": {
            "half_life_days": half_life,
            "outlier_threshold": outlier_threshold,
            "dampening_factor": dampening_factor,
            "reference_date": reference_date,
            "hierarchy_levels": hierarchy_levels,
            "value_columns": value_cols
        }
    }

    input_summary = {
        "record_count": len(raw_records),
        "date_range": {
            "min": min(r["transaction_date"] for r in raw_records),
            "max": max(r["transaction_date"] for r in raw_records)
        },
        "hierarchy_validation": hierarchy_validation,
        "recency_score": recency_score,
        "weight_statistics": weight_stats
    }

    diagnostics = {
        "outlier_detection": outlier_summary,
        "contribution_statistics": contribution_stats,
        "rollup_summary": rollup_summary,
        "normalization": normalization_diag
    }

    output = format_pipeline_output(
        normalized_data, pipeline_metadata, diagnostics, input_summary
    )

    write_json_output(output, output_path)
    summary_line = generate_summary_line(output)
    print(f"[Pipeline] Complete: {summary_line}")
    print(f"[Pipeline] Output written to: {output_path}")

    return output


def main():
    """Command-line entry point for the pipeline."""
    if len(sys.argv) < 3:
        print("Usage: python pipeline.py <input.json> <output.json> [--half-life N] [--threshold N]")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    # Parse optional arguments
    half_life = DEFAULT_HALF_LIFE
    threshold = DEFAULT_OUTLIER_THRESHOLD

    i = 3
    while i < len(sys.argv):
        if sys.argv[i] == "--half-life" and i + 1 < len(sys.argv):
            half_life = float(sys.argv[i + 1])
            i += 2
        elif sys.argv[i] == "--threshold" and i + 1 < len(sys.argv):
            threshold = float(sys.argv[i + 1])
            i += 2
        else:
            i += 1

    try:
        run_pipeline(input_path, output_path, half_life=half_life,
                     outlier_threshold=threshold)
    except Exception as e:
        print(f"[Pipeline] ERROR: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
