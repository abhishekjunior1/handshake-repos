"""
Integrity Checker Module

Checks referential integrity between tables. Validates that foreign key
values in one table have corresponding entries in the referenced table
and column. Reports violations when orphaned references are found.
"""

from typing import Any, Dict, List, Set


def check_referential_integrity(
    records: List[Dict[str, Any]],
    foreign_key_def: Dict[str, Any],
    reference_values: Set[str]
) -> List[Dict[str, Any]]:
    """Check referential integrity for a foreign key relationship.

    Validates that all foreign key values in the source records exist
    in the set of valid reference values from the target table.

    Args:
        records: List of records containing the foreign key column.
        foreign_key_def: Definition of the foreign key relationship,
            including 'column' (source column name).
        reference_values: Set of valid values from the target table/column
            that foreign keys must reference.

    Returns:
        List of violation dictionaries for orphaned references.
    """
    violations = []
    source_column = foreign_key_def.get("column")
    target_table = foreign_key_def.get("references_table", "unknown")
    target_column = foreign_key_def.get("references_column", "unknown")

    if not source_column:
        return violations

    for idx, record in enumerate(records):
        if source_column not in record:
            continue

        value = record[source_column]
        if value is None:
            continue

        str_value = str(value)
        if str_value not in reference_values:
            violations.append({
                "record_index": idx,
                "column": source_column,
                "rule": "referential_integrity",
                "value": str_value,
                "message": (
                    f"Foreign key value '{str_value}' in column '{source_column}' "
                    f"has no matching entry in {target_table}.{target_column}"
                )
            })

    return violations


def validate_cross_table_refs(
    tables: Dict[str, List[Dict[str, Any]]],
    schema: Dict[str, Any]
) -> Dict[str, List[Dict[str, Any]]]:
    """Validate all cross-table referential integrity constraints.

    Iterates through all foreign key definitions in the schema and
    checks that references between tables are valid.

    Args:
        tables: Dictionary mapping table names to their records.
        schema: Full schema definition containing foreign key declarations.

    Returns:
        Dictionary mapping table names to their integrity violations.
    """
    all_violations = {}
    table_schemas = schema.get("tables", {})

    for table_name, table_schema in table_schemas.items():
        foreign_keys = table_schema.get("foreign_keys", [])
        records = tables.get(table_name, [])
        table_violations = []

        for fk_def in foreign_keys:
            ref_table = fk_def.get("references_table")
            ref_column = fk_def.get("references_column")

            if ref_table not in tables:
                continue

            ref_records = tables[ref_table]
            reference_values = _extract_column_values(ref_records, ref_column)

            violations = check_referential_integrity(
                records, fk_def, reference_values
            )
            table_violations.extend(violations)

        if table_violations:
            all_violations[table_name] = table_violations

    return all_violations


def _extract_column_values(
    records: List[Dict[str, Any]], column: str
) -> Set[str]:
    """Extract unique values from a specific column across all records.

    Args:
        records: List of data records.
        column: Column name to extract values from.

    Returns:
        Set of string representations of unique values in the column.
    """
    values = set()
    for record in records:
        if column in record and record[column] is not None:
            values.add(str(record[column]))
    return values


def get_foreign_key_definitions(
    schema: Dict[str, Any], table_name: str
) -> List[Dict[str, Any]]:
    """Get foreign key definitions for a specific table.

    Args:
        schema: Full schema definition.
        table_name: Name of the table to get FK definitions for.

    Returns:
        List of foreign key definition dictionaries.
    """
    table_schemas = schema.get("tables", {})
    table_schema = table_schemas.get(table_name, {})
    return table_schema.get("foreign_keys", [])
