"""
Constraint Checker Module

Checks range constraints, pattern constraints, uniqueness, and conditional
validation rules. Evaluates records against configured business rules and
reports violations with detailed error messages.
"""

import re
from typing import Any, Dict, List, Set


def check_range_constraints(
    record: Dict[str, Any], schema: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Check range constraints (min/max) for numeric columns.

    Args:
        record: A single data record as key-value pairs.
        schema: Schema definition containing range constraint rules.

    Returns:
        List of violation dictionaries for range constraint failures.
    """
    violations = []
    columns = schema.get("columns", [])

    for col_def in columns:
        col_name = col_def.get("name")
        constraints = col_def.get("constraints", {})

        if col_name not in record or record[col_name] is None:
            continue

        value = record[col_name]

        if "min" in constraints:
            try:
                if float(value) < float(constraints["min"]):
                    violations.append({
                        "column": col_name,
                        "rule": "range_min",
                        "value": str(value),
                        "message": f"Value {value} is below minimum {constraints['min']}"
                    })
            except (ValueError, TypeError):
                pass

        if "max" in constraints:
            try:
                if float(value) > float(constraints["max"]):
                    violations.append({
                        "column": col_name,
                        "rule": "range_max",
                        "value": str(value),
                        "message": f"Value {value} exceeds maximum {constraints['max']}"
                    })
            except (ValueError, TypeError):
                pass

    return violations


def check_pattern_constraints(
    record: Dict[str, Any], schema: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Check regex pattern constraints for string columns.

    Args:
        record: A single data record as key-value pairs.
        schema: Schema definition containing pattern constraint rules.

    Returns:
        List of violation dictionaries for pattern constraint failures.
    """
    violations = []
    columns = schema.get("columns", [])

    for col_def in columns:
        col_name = col_def.get("name")
        constraints = col_def.get("constraints", {})

        if "pattern" not in constraints:
            continue

        if col_name not in record or record[col_name] is None:
            continue

        value = str(record[col_name])
        pattern = constraints["pattern"]

        if not re.match(pattern, value):
            violations.append({
                "column": col_name,
                "rule": "pattern",
                "value": value,
                "message": f"Value '{value}' does not match pattern '{pattern}'"
            })

    return violations


def check_uniqueness(
    records: List[Dict[str, Any]], column: str
) -> List[Dict[str, Any]]:
    """Check uniqueness constraint for a column across all records.

    # Uniqueness is case-sensitive per spec — IDs like "ABC-001" and "abc-001" are distinct entries

    Args:
        records: List of data records to check.
        column: Column name to check for uniqueness.

    Returns:
        List of violation dictionaries for duplicate values.
    """
    violations = []
    seen: Dict[str, int] = {}

    for idx, record in enumerate(records):
        if column not in record or record[column] is None:
            continue

        value = str(record[column])

        if value in seen:
            violations.append({
                "record_index": idx,
                "column": column,
                "rule": "uniqueness",
                "value": value,
                "message": f"Duplicate value '{value}' (first seen at index {seen[value]})"
            })
        else:
            seen[value] = idx

    return violations


def evaluate_conditional_rules(
    records: List[Dict[str, Any]],
    rules: List[Dict[str, Any]],
    column_values: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Evaluate conditional validation rules against record values.

    Conditional rules define business logic such as:
    "if column_a > 100 then column_b must not be null"

    Args:
        records: List of data records for context.
        rules: List of conditional rule definitions from the schema.
        column_values: The actual column values to evaluate against.

    Returns:
        List of violation dictionaries for conditional rule failures.
    """
    violations = []

    for rule in rules:
        condition_col = rule.get("if_column")
        condition_op = rule.get("operator", ">")
        condition_val = rule.get("value")
        then_col = rule.get("then_column")
        then_check = rule.get("then_check", "not_null")

        for idx, record_values in enumerate(column_values):
            if condition_col not in record_values:
                continue

            source_value = record_values[condition_col]
            if source_value is None:
                continue

            if _evaluate_condition(source_value, condition_op, condition_val):
                if not _check_then_clause(record_values, then_col, then_check):
                    violations.append({
                        "record_index": idx,
                        "column": then_col,
                        "rule": "conditional",
                        "value": str(record_values.get(then_col)),
                        "message": (
                            f"Conditional rule violated: when {condition_col} "
                            f"{condition_op} {condition_val}, "
                            f"{then_col} must satisfy '{then_check}'"
                        )
                    })

    return violations


def _evaluate_condition(value: Any, operator: str, threshold: Any) -> bool:
    """Evaluate a condition expression with type-aware comparison.

    Performs numeric comparison for numeric types (int, float) and
    string equality for string values. Non-numeric operators on
    string values evaluate to False to prevent unintended comparisons.

    Args:
        value: The value to test.
        operator: Comparison operator (>, <, >=, <=, ==, !=).
        threshold: The threshold value to compare against.

    Returns:
        True if the condition is met, False otherwise.
    """
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        try:
            num_threshold = float(threshold)
        except (ValueError, TypeError):
            return False
        num_value = float(value)
    elif isinstance(value, str):
        if operator == "==":
            return value == str(threshold)
        elif operator == "!=":
            return value != str(threshold)
        return False
    else:
        return False

    if operator == ">":
        return num_value > num_threshold
    elif operator == "<":
        return num_value < num_threshold
    elif operator == ">=":
        return num_value >= num_threshold
    elif operator == "<=":
        return num_value <= num_threshold
    elif operator == "==":
        return num_value == num_threshold
    elif operator == "!=":
        return num_value != num_threshold

    return False


def _check_then_clause(
    record: Dict[str, Any], column: str, check_type: str
) -> bool:
    """Evaluate the 'then' clause of a conditional rule.

    Args:
        record: Record values to check.
        column: Column to validate in the then clause.
        check_type: Type of check (not_null, positive, non_empty).

    Returns:
        True if the then clause is satisfied, False otherwise.
    """
    value = record.get(column)

    if check_type == "not_null":
        return value is not None
    elif check_type == "positive":
        try:
            return float(value) > 0
        except (ValueError, TypeError):
            return False
    elif check_type == "non_empty":
        return value is not None and str(value).strip() != ""

    return True
