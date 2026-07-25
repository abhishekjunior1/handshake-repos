"""Result formatter module for the analytical query engine.

Formats query results into structured output with metadata,
handles SELECT column projection, ORDER BY sorting, and LIMIT/OFFSET.
"""

from typing import Any
from functools import cmp_to_key


def format_query_result(
    rows: list[dict],
    query: dict,
    query_index: int,
) -> dict:
    """Format a single query result into the output structure.

    Applies final SELECT projection, ORDER BY, and LIMIT/OFFSET
    before generating the output record.
    """
    projected = _apply_select(rows, query.get("select", []))

    order_by = query.get("order_by")
    if order_by:
        projected = _apply_order_by(projected, order_by)

    limit = query.get("limit")
    offset = query.get("offset", 0)
    if limit is not None:
        projected = projected[offset:offset + limit]
    elif offset > 0:
        projected = projected[offset:]

    return {
        "query_index": query_index,
        "query_type": query["type"],
        "row_count": len(projected),
        "columns": _extract_columns(projected),
        "rows": projected,
    }


def _apply_select(rows: list[dict], select_cols: list[str]) -> list[dict]:
    """Project rows to only include specified columns.

    If select_cols contains '*', all columns are included.
    """
    if not rows:
        return []

    if select_cols == ["*"] or not select_cols:
        return [dict(row) for row in rows]

    projected = []
    for row in rows:
        new_row = {}
        for col_spec in select_cols:
            new_row[col_spec] = row.get(col_spec)
        projected.append(new_row)
    return projected


def _apply_order_by(rows: list[dict], order_by: list[dict]) -> list[dict]:
    """Sort results by ORDER BY specification.

    NULL values are sorted LAST regardless of sort direction,
    following SQL standard NULLS LAST behavior.
    """
    if not order_by or not rows:
        return rows

    def compare_rows(a, b):
        for spec in order_by:
            col = spec["column"]
            desc = spec.get("direction", "asc").lower() == "desc"
            val_a = a.get(col)
            val_b = b.get(col)

            # NULLs always sort last (SQL standard NULLS LAST)
            if val_a is None and val_b is None:
                continue
            if val_a is None:
                return 1
            if val_b is None:
                return -1

            if val_a < val_b:
                return 1 if desc else -1
            elif val_a > val_b:
                return -1 if desc else 1

        return 0

    return sorted(rows, key=cmp_to_key(compare_rows))


def _extract_columns(rows: list[dict]) -> list[str]:
    """Extract column names from result rows in stable order."""
    if not rows:
        return []
    seen = set()
    columns = []
    for row in rows:
        for col in row.keys():
            if col not in seen:
                seen.add(col)
                columns.append(col)
    return columns


def build_output(results: list[dict], metadata: dict) -> dict:
    """Build the final output structure with all query results."""
    return {
        "metadata": metadata,
        "results": results,
    }


def build_metadata(config: dict, tables: dict) -> dict:
    """Build execution metadata from configuration."""
    table_info = {}
    for table_name, rows in tables.items():
        table_info[table_name] = {
            "row_count": len(rows),
            "columns": list(rows[0].keys()) if rows else [],
        }

    return {
        "tables_loaded": list(tables.keys()),
        "table_info": table_info,
        "query_count": len(config.get("queries", [])),
    }
