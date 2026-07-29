"""
Catalog manager module for maintaining table statistics, column cardinalities,
and page counts used by the query optimizer.

Provides an interface to access table metadata, column statistics, and index
information from the database configuration.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass
class ColumnStats:
    """Statistics for a single column."""
    name: str
    n_distinct: int
    null_fraction: float
    avg_width: int
    correlation: float


@dataclass
class IndexInfo:
    """Metadata about a database index."""
    name: str
    columns: List[str]
    is_unique: bool
    is_primary: bool
    table_name: str


@dataclass
class TableStats:
    """Complete statistics for a table."""
    name: str
    n_rows: int
    total_pages: int
    pages_in_buffer: int
    last_analyze_timestamp: int
    last_modified_timestamp: int
    columns: Dict[str, ColumnStats]
    indexes: Dict[str, IndexInfo]


class CatalogManager:
    """Manages database catalog information including table and column statistics."""

    def __init__(self, config: dict):
        self._config = config
        self._tables: Dict[str, TableStats] = {}
        self._load_catalog()

    def _load_catalog(self):
        """Load all table statistics from configuration."""
        tables_config = self._config.get("tables", {})
        for table_name, table_data in tables_config.items():
            columns = {}
            for col_name, col_data in table_data.get("columns", {}).items():
                columns[col_name] = ColumnStats(
                    name=col_name,
                    n_distinct=col_data["n_distinct"],
                    null_fraction=col_data.get("null_fraction", 0.0),
                    avg_width=col_data.get("avg_width", 4),
                    correlation=col_data.get("correlation", 0.0)
                )

            indexes = {}
            for idx_name, idx_data in table_data.get("indexes", {}).items():
                indexes[idx_name] = IndexInfo(
                    name=idx_name,
                    columns=idx_data["columns"],
                    is_unique=idx_data.get("is_unique", False),
                    is_primary=idx_data.get("is_primary", False),
                    table_name=table_name
                )

            self._tables[table_name] = TableStats(
                name=table_name,
                n_rows=table_data["n_rows"],
                total_pages=table_data["total_pages"],
                pages_in_buffer=table_data.get("pages_in_buffer", 0),
                last_analyze_timestamp=table_data.get("last_analyze_timestamp", 0),
                last_modified_timestamp=table_data.get("last_modified_timestamp", 0),
                columns=columns,
                indexes=indexes
            )

    def get_table_stats(self, table_name: str) -> Optional[TableStats]:
        """Retrieve statistics for a given table."""
        return self._tables.get(table_name)

    def get_column_stats(self, table_name: str, column_name: str) -> Optional[ColumnStats]:
        """Retrieve statistics for a specific column in a table."""
        table = self._tables.get(table_name)
        if table:
            return table.columns.get(column_name)
        return None

    def get_table_row_count(self, table_name: str) -> int:
        """Get the estimated row count for a table."""
        table = self._tables.get(table_name)
        return table.n_rows if table else 0

    def get_column_distinct_count(self, table_name: str, column_name: str) -> int:
        """Get the number of distinct values for a column."""
        col = self.get_column_stats(table_name, column_name)
        return col.n_distinct if col else 1

    def get_table_pages(self, table_name: str) -> int:
        """Get total pages for a table."""
        table = self._tables.get(table_name)
        return table.total_pages if table else 0

    def get_pages_in_buffer(self, table_name: str) -> int:
        """Get pages currently in buffer pool for a table."""
        table = self._tables.get(table_name)
        return table.pages_in_buffer if table else 0

    def get_indexes_for_table(self, table_name: str) -> List[IndexInfo]:
        """Get all indexes defined on a table."""
        table = self._tables.get(table_name)
        if table:
            return list(table.indexes.values())
        return []

    def get_index_for_column(self, table_name: str, column_name: str) -> Optional[IndexInfo]:
        """Find an index that has the given column as its leading column."""
        table = self._tables.get(table_name)
        if not table:
            return None
        for idx in table.indexes.values():
            if idx.columns and idx.columns[0] == column_name:
                return idx
        return None

    def get_covering_index(self, table_name: str, needed_columns: List[str]) -> Optional[IndexInfo]:
        """Find an index that covers all needed columns."""
        table = self._tables.get(table_name)
        if not table:
            return None
        for idx in table.indexes.values():
            if set(needed_columns).issubset(set(idx.columns)):
                return idx
        return None

    def get_column_correlation(self, table_name: str, column_name: str) -> float:
        """Get the physical correlation of a column's values with heap order."""
        col = self.get_column_stats(table_name, column_name)
        return abs(col.correlation) if col else 0.0

    def get_null_fraction(self, table_name: str, column_name: str) -> float:
        """Get the fraction of NULL values in a column."""
        col = self.get_column_stats(table_name, column_name)
        return col.null_fraction if col else 0.0

    def get_all_table_names(self) -> List[str]:
        """Get all table names in the catalog."""
        return list(self._tables.keys())

    def get_table_last_analyze(self, table_name: str) -> int:
        """Get the timestamp of the last ANALYZE run on a table."""
        table = self._tables.get(table_name)
        return table.last_analyze_timestamp if table else 0

    def get_table_last_modified(self, table_name: str) -> int:
        """Get the timestamp of the last modification to a table."""
        table = self._tables.get(table_name)
        return table.last_modified_timestamp if table else 0
