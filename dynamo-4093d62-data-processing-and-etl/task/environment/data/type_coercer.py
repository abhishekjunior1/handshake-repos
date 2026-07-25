"""
Type Coercer Module

Coerces string values to their declared types based on schema definitions.
Handles conversion of string representations to int, float, bool, and date
types. Returns coerced records for downstream constraint checking.
"""

from typing import Any, Dict, List, Optional


def coerce_value(value: Any, target_type: str) -> Any:
    """Coerce a single value to the specified target type.

    Attempts type conversion from string representation to the declared
    type. Returns the original value if coercion is not possible or
    not applicable.

    Args:
        value: The value to coerce.
        target_type: Target type string (int, float, bool, date, string).

    Returns:
        The coerced value, or the original if coercion fails or is unnecessary.
    """
    if value is None:
        return None

    if target_type in ("string", "str"):
        return str(value) if not isinstance(value, str) else value

    if target_type in ("int", "integer"):
        if isinstance(value, int) and not isinstance(value, bool):
            return value
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return value

    if target_type in ("float", "number"):
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        try:
            return float(str(value))
        except (ValueError, TypeError):
            return value

    if target_type == "bool":
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes"):
                return True
            elif value.lower() in ("false", "0", "no"):
                return False
        return value

    if target_type == "date":
        return str(value) if not isinstance(value, str) else value

    return value


def coerce_record(record: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """Coerce all values in a record according to the schema type definitions.

    Args:
        record: A single data record as key-value pairs.
        schema: Schema definition containing column type declarations.

    Returns:
        New dictionary with values coerced to their declared types.
    """
    coerced = {}
    columns = schema.get("columns", [])
    col_types = {col["name"]: col.get("type", "string") for col in columns}

    for key, value in record.items():
        target_type = col_types.get(key, "string")
        coerced[key] = coerce_value(value, target_type)

    return coerced


def apply_coercion(
    records: List[Dict[str, Any]], schema: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Apply type coercion to all records in a dataset.

    Args:
        records: List of data records to coerce.
        schema: Schema definition containing column type declarations.

    Returns:
        List of new records with coerced values.
    """
    coerced_records = []
    for record in records:
        coerced_records.append(coerce_record(record, schema))
    return coerced_records
