"""
Index advisor module for index selection and covering index detection.

Analyzes query predicates and access patterns to recommend optimal index
usage and identifies opportunities for index-only scans.
"""

import math
from typing import Dict, List, Optional, Tuple
from catalog_manager import CatalogManager, IndexInfo, ColumnStats
from query_parser import QueryAST, Predicate


class IndexRecommendation:
    """Represents an index usage recommendation."""

    def __init__(self, index: IndexInfo, benefit_score: float,
                 access_type: str, columns_used: List[str]):
        self.index = index
        self.benefit_score = benefit_score
        self.access_type = access_type
        self.columns_used = columns_used


class IndexAdvisor:
    """Advises on index selection and detects covering index opportunities."""

    def __init__(self, catalog: CatalogManager, config: dict):
        self._catalog = catalog
        self._fill_factor = config.get("default_fill_factor", 0.9)
        self._page_capacity = config.get("page_capacity", 256)
        self._random_page_cost = config.get("random_page_cost", 4.0)

    def recommend_indexes(self, query: QueryAST,
                          table_name: str) -> List[IndexRecommendation]:
        """Recommend indexes for a table based on query predicates."""
        recommendations = []
        table_stats = self._catalog.get_table_stats(table_name)
        if not table_stats:
            return recommendations

        filter_columns = self._get_filter_columns(query, table_name)
        join_columns = self._get_join_columns(query, table_name)

        all_candidate_columns = list(set(filter_columns + join_columns))

        for column in all_candidate_columns:
            index = self._catalog.get_index_for_column(table_name, column)
            if index:
                score = self._compute_index_benefit(
                    table_name, index, column, query
                )
                access_type = self._determine_access_type(index, query, table_name)
                recommendations.append(IndexRecommendation(
                    index=index,
                    benefit_score=score,
                    access_type=access_type,
                    columns_used=[column]
                ))

        covering = self._detect_covering_index(query, table_name)
        if covering:
            recommendations.append(covering)

        recommendations.sort(key=lambda r: r.benefit_score, reverse=True)
        return recommendations

    def _get_filter_columns(self, query: QueryAST, table_name: str) -> List[str]:
        """Get columns used in filter predicates for a table."""
        columns = []
        for predicate in query.predicates:
            if predicate.is_join_predicate:
                continue
            if predicate.left.table_alias:
                resolved_table = query.alias_map.get(
                    predicate.left.table_alias, predicate.left.table_alias
                )
                if resolved_table == table_name:
                    columns.append(predicate.left.column_name)
        return columns

    def _get_join_columns(self, query: QueryAST, table_name: str) -> List[str]:
        """Get columns used in join predicates for a table."""
        columns = []
        for join in query.joins:
            if join.left_table == table_name:
                columns.append(join.left_column)
            if join.right_table == table_name:
                columns.append(join.right_column)
        return columns

    def _compute_index_benefit(self, table_name: str, index: IndexInfo,
                                column: str, query: QueryAST) -> float:
        """Compute the benefit score of using an index."""
        n_rows = self._catalog.get_table_row_count(table_name)
        n_distinct = self._catalog.get_column_distinct_count(table_name, column)
        total_pages = self._catalog.get_table_pages(table_name)

        tree_height = self._estimate_btree_height(n_rows)

        selectivity = 1.0 / max(n_distinct, 1)
        estimated_rows = max(1, int(n_rows * selectivity))

        seq_cost = total_pages
        index_cost = tree_height + estimated_rows

        benefit = max(0, seq_cost - index_cost) / max(seq_cost, 1)

        if index.is_unique and selectivity <= 1.0 / n_rows:
            benefit *= 1.5

        return round(benefit, 4)

    def _estimate_btree_height(self, n_rows: int) -> int:
        """
        Estimate B-tree index height using PostgreSQL convention.

        Height is calculated as the number of levels needed to index all rows
        given the effective branching factor (fill_factor * page_capacity).
        """
        if n_rows <= 0:
            return 1
        effective_fanout = self._fill_factor * self._page_capacity
        height = math.ceil(math.log(max(n_rows, 1)) / math.log(max(effective_fanout, 2)))
        return max(1, height)

    def _determine_access_type(self, index: IndexInfo, query: QueryAST,
                                table_name: str) -> str:
        """Determine the type of index access (scan, seek, or index-only)."""
        select_columns = set()
        for col in query.select_columns:
            if col.table_alias:
                resolved = query.alias_map.get(col.table_alias, col.table_alias)
                if resolved == table_name:
                    select_columns.add(col.column_name)

        filter_columns = set(self._get_filter_columns(query, table_name))
        needed = select_columns | filter_columns

        if needed.issubset(set(index.columns)):
            return "Index Only Scan"

        if index.is_unique:
            return "Index Seek"

        return "Index Scan"

    def _detect_covering_index(self, query: QueryAST,
                                table_name: str) -> Optional[IndexRecommendation]:
        """Detect if a covering index exists for the query on this table."""
        needed_columns = set()

        for col in query.select_columns:
            if col.table_alias:
                resolved = query.alias_map.get(col.table_alias, col.table_alias)
                if resolved == table_name:
                    needed_columns.add(col.column_name)

        for pred in query.predicates:
            if pred.left.table_alias:
                resolved = query.alias_map.get(
                    pred.left.table_alias, pred.left.table_alias
                )
                if resolved == table_name:
                    needed_columns.add(pred.left.column_name)

        for join in query.joins:
            if join.left_table == table_name:
                needed_columns.add(join.left_column)
            if join.right_table == table_name:
                needed_columns.add(join.right_column)

        if not needed_columns:
            return None

        covering_idx = self._catalog.get_covering_index(
            table_name, list(needed_columns)
        )
        if covering_idx:
            return IndexRecommendation(
                index=covering_idx,
                benefit_score=0.95,
                access_type="Index Only Scan",
                columns_used=list(needed_columns)
            )
        return None

    def get_index_stats(self, table_name: str) -> List[Dict]:
        """Get statistics about all indexes on a table."""
        indexes = self._catalog.get_indexes_for_table(table_name)
        stats = []
        for idx in indexes:
            n_rows = self._catalog.get_table_row_count(table_name)
            stats.append({
                "name": idx.name,
                "columns": idx.columns,
                "is_unique": idx.is_unique,
                "estimated_height": self._estimate_btree_height(n_rows),
                "is_primary": idx.is_primary
            })
        return stats
