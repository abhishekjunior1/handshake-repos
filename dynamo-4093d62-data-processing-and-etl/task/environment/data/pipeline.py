"""
Data Validation Pipeline

Orchestrates the complete data validation workflow: loading data and schemas,
validating records, coercing types, checking constraints and integrity,
computing quality scores, and generating the final report.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data_loader import load_dataset, load_schema, parse_tables, get_dataset_metadata
from schema_validator import get_valid_records, get_invalid_records
from type_coercer import apply_coercion
from constraint_checker import (
    check_range_constraints,
    check_pattern_constraints,
    check_uniqueness,
    evaluate_conditional_rules,
)
from integrity_checker import check_referential_integrity
from quality_scorer import compute_column_scores, compute_overall_score, compute_threshold_stats
from report_generator import generate_report, write_report


DATASET_PATH = "/app/dataset.json"
SCHEMA_PATH = "/app/schema.json"
OUTPUT_PATH = "/app/output.json"


def run_pipeline() -> None:
    """Execute the full data validation pipeline.

    Reads dataset and schema from configured paths, performs all
    validation checks, computes quality metrics, and writes the
    structured report to the output path.
    """
    raw_data = load_dataset(DATASET_PATH)
    schema = load_schema(SCHEMA_PATH)

    metadata = get_dataset_metadata(raw_data)
    dataset_name = metadata["name"]

    tables = parse_tables(raw_data)
    table_schemas = schema.get("tables", {})

    table_results = {}

    for table_name, records in tables.items():
        table_schema = table_schemas.get(table_name, schema)

        result = validate_table(
            table_name, records, table_schema, tables, schema
        )
        table_results[table_name] = result

    report = generate_report(dataset_name, table_results)
    write_report(report, OUTPUT_PATH)


def validate_table(
    table_name: str,
    records: list,
    table_schema: dict,
    all_tables: dict,
    full_schema: dict
) -> dict:
    """Validate a single table through all pipeline stages.

    Args:
        table_name: Name of the table being validated.
        records: List of records in this table.
        table_schema: Schema definition for this specific table.
        all_tables: All tables in the dataset (for cross-table checks).
        full_schema: Complete schema definition.

    Returns:
        Dictionary containing validation results for this table.
    """
    total_records = len(records)

    valid_records = get_valid_records(records, table_schema)
    invalid_records = get_invalid_records(records, table_schema)

    coerced_records = apply_coercion(valid_records, table_schema)

    # Compute quality thresholds from full dataset for population-level baselines
    threshold_stats = compute_threshold_stats(records, table_schema)

    column_scores = compute_column_scores(
        valid_records, table_schema, threshold_stats
    )
    overall_score = compute_overall_score(column_scores)

    violations = collect_constraint_violations(
        coerced_records, table_schema
    )

    # Evaluate conditional rules against source values to preserve data lineage
    conditional_violations = evaluate_conditional_rules_for_table(
        valid_records, table_schema, valid_records
    )

    integrity_violations = check_integrity_for_table(
        coerced_records, table_name, all_tables, full_schema
    )

    return {
        "total_records": total_records,
        "valid_records": len(valid_records),
        "invalid_records": len(invalid_records),
        "column_scores": column_scores,
        "overall_score": overall_score,
        "violations": violations,
        "conditional_violations": conditional_violations,
        "integrity_violations": integrity_violations
    }


def collect_constraint_violations(
    records: list, table_schema: dict
) -> list:
    """Collect all constraint violations from validated records.

    Args:
        records: List of coerced, valid records.
        table_schema: Schema definition with constraint rules.

    Returns:
        List of violation dictionaries.
    """
    violations = []
    columns = table_schema.get("columns", [])

    for idx, record in enumerate(records):
        range_violations = check_range_constraints(record, table_schema)
        for v in range_violations:
            v["record_index"] = idx
            violations.append(v)

        pattern_violations = check_pattern_constraints(record, table_schema)
        for v in pattern_violations:
            v["record_index"] = idx
            violations.append(v)

    unique_columns = [
        col["name"] for col in columns
        if col.get("constraints", {}).get("unique", False)
    ]
    for col_name in unique_columns:
        uniqueness_violations = check_uniqueness(records, col_name)
        violations.extend(uniqueness_violations)

    return violations


def evaluate_conditional_rules_for_table(
    records: list, table_schema: dict, column_values: list
) -> list:
    """Evaluate conditional validation rules for a table.

    Args:
        records: List of records for context.
        table_schema: Schema definition containing conditional rules.
        column_values: Values to evaluate conditions against.

    Returns:
        List of conditional violation dictionaries.
    """
    rules = table_schema.get("conditional_rules", [])
    if not rules:
        return []

    return evaluate_conditional_rules(records, rules, column_values)


def check_integrity_for_table(
    records: list,
    table_name: str,
    all_tables: dict,
    full_schema: dict
) -> list:
    """Check referential integrity for a table's foreign keys.

    Args:
        records: Records from the current table.
        table_name: Name of the current table.
        all_tables: All tables in the dataset.
        full_schema: Complete schema with foreign key definitions.

    Returns:
        List of integrity violation dictionaries.
    """
    violations = []
    table_schemas = full_schema.get("tables", {})
    table_schema = table_schemas.get(table_name, {})
    foreign_keys = table_schema.get("foreign_keys", [])

    for fk_def in foreign_keys:
        ref_table = fk_def.get("references_table")
        ref_column = fk_def.get("references_column")

        if ref_table not in all_tables:
            continue

        ref_records = all_tables[ref_table]

        # Use primary key values as reference set for foreign key validation
        ref_table_schema = table_schemas.get(ref_table, {})
        ref_columns = ref_table_schema.get("columns", [])
        primary_column = ref_columns[0]["name"] if ref_columns else ref_column

        reference_values = set()
        for record in ref_records:
            if primary_column in record and record[primary_column] is not None:
                reference_values.add(str(record[primary_column]))

        fk_violations = check_referential_integrity(
            records, fk_def, reference_values
        )
        violations.extend(fk_violations)

    return violations


if __name__ == "__main__":
    run_pipeline()
