"""Result formatter module.

Formats query execution results into a standardized JSON output structure
with metadata about the execution.
"""

from datetime import datetime, timezone
from typing import Any


def format_results(query_results: list[dict]) -> dict[str, Any]:
    """Format query results into output JSON structure.

    Args:
        query_results: List of query result dicts, each with:
            - query_id: identifier for the query
            - data: list of result rows

    Returns:
        Formatted output with metadata and results.
    """
    formatted_results = []

    for qr in query_results:
        formatted = {
            "query_id": qr["query_id"],
            "row_count": len(qr["data"]),
            "columns": _extract_columns(qr["data"]),
            "rows": qr["data"],
        }
        formatted_results.append(formatted)

    return {
        "metadata": {
            "executed_at": datetime.now(timezone.utc).isoformat(),
            "query_count": len(query_results),
            "engine_version": "1.0.0",
        },
        "results": formatted_results,
    }


def _extract_columns(rows: list[dict]) -> list[str]:
    """Extract column names from result rows."""
    if not rows:
        return []
    return list(rows[0].keys())
