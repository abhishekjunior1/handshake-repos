"""
Report Generator Module

Generates structured JSON validation reports containing per-table
quality metrics, column scores, and categorized violation records.
Output format is deterministic and suitable for downstream consumption.
"""

import json
from typing import Any, Dict, List


def generate_report(
    dataset_name: str,
    table_results: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a structured validation report for the entire dataset.

    Assembles results from all validation stages into a unified report
    with consistent structure per table.

    Args:
        dataset_name: Name identifier for the dataset.
        table_results: Dictionary mapping table names to their validation
            results including scores, violations, and record counts.

    Returns:
        Complete report dictionary ready for JSON serialization.
    """
    report = {
        "dataset": dataset_name,
        "tables": {}
    }

    for table_name, results in table_results.items():
        report["tables"][table_name] = {
            "total_records": results.get("total_records", 0),
            "valid_records": results.get("valid_records", 0),
            "invalid_records": results.get("invalid_records", 0),
            "column_scores": results.get("column_scores", {}),
            "overall_score": results.get("overall_score", 0.0),
            "violations": results.get("violations", []),
            "conditional_violations": results.get("conditional_violations", []),
            "integrity_violations": results.get("integrity_violations", [])
        }

    return report


def format_violation(
    record_index: int,
    column: str,
    rule: str,
    value: str,
    message: str
) -> Dict[str, Any]:
    """Create a standardized violation record.

    Args:
        record_index: Index of the offending record in the dataset.
        column: Column name where the violation occurred.
        rule: Type of validation rule that was violated.
        value: The offending value as a string.
        message: Human-readable description of the violation.

    Returns:
        Violation dictionary with standardized structure.
    """
    return {
        "record_index": record_index,
        "column": column,
        "rule": rule,
        "value": value,
        "message": message
    }


def write_report(report: Dict[str, Any], output_path: str) -> None:
    """Write the validation report to a JSON file.

    Args:
        report: Complete report dictionary to serialize.
        output_path: File path to write the JSON report to.
    """
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False, sort_keys=False)


def summarize_report(report: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a summary of the validation report.

    Args:
        report: Complete validation report.

    Returns:
        Summary dictionary with aggregate statistics.
    """
    total_tables = len(report.get("tables", {}))
    total_violations = 0
    total_records = 0

    for table_data in report.get("tables", {}).values():
        total_records += table_data.get("total_records", 0)
        total_violations += len(table_data.get("violations", []))
        total_violations += len(table_data.get("conditional_violations", []))
        total_violations += len(table_data.get("integrity_violations", []))

    return {
        "total_tables": total_tables,
        "total_records": total_records,
        "total_violations": total_violations
    }
