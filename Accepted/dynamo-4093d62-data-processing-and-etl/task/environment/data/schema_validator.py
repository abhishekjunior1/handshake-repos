"""
Schema Validator Module

Validates records against schema column definitions. Checks that each
record conforms to declared column types and nullability constraints.
Separates valid records from invalid ones for downstream processing.
"""

from typing import Any, Dict, List, Tuple


# Supported type mappings for validation
VALID_TYPES = {"string", "int", "float", "bool", "date", "integer", "number"}


def validate_column_types(record: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Validate that record values conform to declared column types.

    Args:
        record: A single data record as key-value pairs.
        schema: Schema definition containing column type declarations.

    Returns:
        List of error messages for type violations found.
    """
    errors = []
    columns = schema.get("columns", [])

    for col_def in columns:
        col_name = col_def.get("name")
        col_type = col_def.get("type", "string")

        if col_name not in record:
            continue

        value = record[col_name]

        if value is None:
            continue

        if not _is_valid_type(value, col_type):
            errors.append(
                f"Column '{col_name}': expected type '{col_type}', "
                f"got value '{value}' of type '{type(value).__name__}'"
            )

    return errors


def check_nullability(record: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """Check nullability constraints for a record.

    # Null/None values are valid for optional fields — only flag nulls in required columns

    Args:
        record: A single data record as key-value pairs.
        schema: Schema definition containing column nullability rules.

    Returns:
        List of error messages for nullability violations.
    """
    errors = []
    columns = schema.get("columns", [])

    for col_def in columns:
        col_name = col_def.get("name")
        required = col_def.get("required", False)

        if required:
            if col_name not in record or record[col_name] is None:
                errors.append(
                    f"Column '{col_name}': required field is null or missing"
                )

    return errors


def get_valid_records(
    records: List[Dict[str, Any]], schema: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Filter records that pass all schema validation checks.

    Args:
        records: List of data records to validate.
        schema: Schema definition to validate against.

    Returns:
        List of records that conform to the schema.
    """
    valid = []
    for record in records:
        type_errors = validate_column_types(record, schema)
        null_errors = check_nullability(record, schema)
        if not type_errors and not null_errors:
            valid.append(record)
    return valid


def get_invalid_records(
    records: List[Dict[str, Any]], schema: Dict[str, Any]
) -> List[Tuple[int, Dict[str, Any], List[str]]]:
    """Identify records that fail schema validation.

    Args:
        records: List of data records to validate.
        schema: Schema definition to validate against.

    Returns:
        List of tuples (record_index, record, error_messages) for failures.
    """
    invalid = []
    for idx, record in enumerate(records):
        type_errors = validate_column_types(record, schema)
        null_errors = check_nullability(record, schema)
        all_errors = type_errors + null_errors
        if all_errors:
            invalid.append((idx, record, all_errors))
    return invalid


def _is_valid_type(value: Any, expected_type: str) -> bool:
    """Check if a value matches or is coercible to the expected type.

    Accepts both native Python types and string representations that
    can be successfully coerced to the target type. This handles the
    common case of JSON data where numeric values arrive as strings.

    Args:
        value: The value to type-check.
        expected_type: The declared type from the schema.

    Returns:
        True if value matches expected type or is coercible, False otherwise.
    """
    if expected_type in ("string", "str"):
        return isinstance(value, str)
    elif expected_type in ("int", "integer"):
        if isinstance(value, int) and not isinstance(value, bool):
            return True
        if isinstance(value, str):
            try:
                int(float(value))
                return True
            except (ValueError, TypeError):
                return False
        return False
    elif expected_type in ("float", "number"):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return True
        if isinstance(value, str):
            try:
                float(value)
                return True
            except (ValueError, TypeError):
                return False
        return False
    elif expected_type == "bool":
        return isinstance(value, bool)
    elif expected_type == "date":
        return isinstance(value, str) and _is_date_format(value)
    return True


def _is_date_format(value: str) -> bool:
    """Check if string matches common date formats (YYYY-MM-DD).

    Args:
        value: String value to check.

    Returns:
        True if value matches a date pattern.
    """
    import re
    date_pattern = r"^\d{4}-\d{2}-\d{2}$"
    return bool(re.match(date_pattern, value))
