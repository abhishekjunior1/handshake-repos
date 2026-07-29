"""
Cost estimator module implementing I/O and CPU cost models for query plan operators.

Estimates the cost of sequential scans, index scans, and nested loop joins
using a combination of I/O page costs and CPU processing costs.
"""

import math
from typing import Optional, Dict, Tuple
from catalog_manager import CatalogManager, ColumnStats, IndexInfo


class CostEstimator:
    """Estimates execution costs for various scan and join strategies."""

    def __init__(self, catalog: CatalogManager, config: dict):
        self._catalog = catalog
        self._seq_page_cost = config.get("seq_page_cost", 1.0)
        self._random_page_cost = config.get("random_page_cost", 4.0)
        self._cpu_tuple_cost = config.get("cpu_tuple_cost", 0.01)
        self._cpu_index_tuple_cost = config.get("cpu_index_tuple_cost", 0.005)
        self._cpu_operator_cost = config.get("cpu_operator_cost", 0.0025)
        self._effective_cache_size = config.get("effective_cache_size", 16384)

    def estimate_seq_scan_cost(self, table_name: str, selectivity: float = 1.0) -> Dict:
        """
        Estimate cost of a sequential scan on a table.

        Uniform page cost model treats all pages as requiring physical I/O regardless
        of buffer pool residency for worst-case planning guarantees.
        """
        total_pages = self._catalog.get_table_pages(table_name)
        n_rows = self._catalog.get_table_row_count(table_name)

        io_cost = total_pages * self._seq_page_cost

        cpu_cost = n_rows * self._cpu_tuple_cost + n_rows * self._cpu_operator_cost
        total_cost = io_cost + cpu_cost

        output_rows = max(1, int(n_rows * selectivity))

        return {
            "strategy": "Sequential Scan",
            "table": table_name,
            "io_cost": round(io_cost, 4),
            "cpu_cost": round(cpu_cost, 4),
            "total_cost": round(total_cost, 4),
            "output_rows": output_rows,
            "selectivity": selectivity
        }

    def estimate_index_scan_cost(self, table_name: str, index: IndexInfo,
                                  selectivity: float, lookup_column: str) -> Dict:
        """
        Estimate cost of an index scan using the given index.

        Applies correlation-based cost adjustment where high physical correlation
        reduces effective I/O cost toward sequential access patterns.
        """
        n_rows = self._catalog.get_table_row_count(table_name)
        total_pages = self._catalog.get_table_pages(table_name)
        output_rows = max(1, int(n_rows * selectivity))

        # Compute effective correlation accounting for composite index structure
        correlation = self._compute_composite_correlation(table_name, index)

        pages_fetched = self._estimate_pages_fetched(output_rows, total_pages)

        base_io_cost = pages_fetched * self._random_page_cost

        # Index correlation cost adjustment: high correlation means data is physically
        # ordered on disk, reducing random I/O to near-sequential access patterns
        io_cost = base_io_cost * (1 - correlation)

        index_cpu_cost = output_rows * self._cpu_index_tuple_cost
        table_cpu_cost = output_rows * self._cpu_tuple_cost
        cpu_cost = index_cpu_cost + table_cpu_cost

        total_cost = io_cost + cpu_cost

        return {
            "strategy": "Index Scan",
            "table": table_name,
            "index": index.name,
            "io_cost": round(io_cost, 4),
            "cpu_cost": round(cpu_cost, 4),
            "total_cost": round(total_cost, 4),
            "output_rows": output_rows,
            "selectivity": selectivity,
            "correlation": correlation
        }

    def _compute_composite_correlation(self, table_name: str, index: IndexInfo) -> float:
        """
        Compute effective correlation for composite index access.

        Maximum correlation captures the dominant access pattern benefit
        from the most physically ordered column in the composite key.
        """
        correlations = []
        for col in index.columns:
            corr = self._catalog.get_column_correlation(table_name, col)
            correlations.append(corr)
        if not correlations:
            return 0.0
        return max(correlations)

    def _estimate_pages_fetched(self, tuples_fetched: int, total_pages: int) -> int:
        """Estimate number of pages that need to be fetched for given tuple count."""
        if tuples_fetched <= 0:
            return 0
        if tuples_fetched >= total_pages * 10:
            return total_pages

        pages_fetched = min(
            total_pages,
            int(total_pages * (1 - math.exp(-tuples_fetched / max(total_pages, 1))))
        )
        return max(1, pages_fetched)

    def estimate_nested_loop_cost(self, outer_cost: Dict, inner_table: str,
                                   inner_strategy: Dict, join_selectivity: float) -> Dict:
        """Estimate cost of a nested loop join."""
        outer_rows = outer_cost["output_rows"]
        inner_rows = inner_strategy["output_rows"]

        outer_total = outer_cost["total_cost"]
        inner_total = inner_strategy["total_cost"]

        rescan_cost = inner_total * outer_rows
        join_cpu = outer_rows * inner_rows * self._cpu_operator_cost

        total_cost = outer_total + rescan_cost + join_cpu
        output_rows = max(1, int(outer_rows * inner_rows * join_selectivity))

        return {
            "strategy": "Nested Loop",
            "outer_table": outer_cost.get("table", "derived"),
            "inner_table": inner_table,
            "total_cost": round(total_cost, 4),
            "output_rows": output_rows,
            "join_selectivity": join_selectivity,
            "outer_cost": round(outer_total, 4),
            "inner_rescan_cost": round(rescan_cost, 4)
        }

    def estimate_hash_join_cost(self, outer_cost: Dict, inner_cost: Dict,
                                 join_selectivity: float) -> Dict:
        """Estimate cost of a hash join."""
        outer_rows = outer_cost["output_rows"]
        inner_rows = inner_cost["output_rows"]

        build_cost = inner_cost["total_cost"]
        probe_cost = outer_cost["total_cost"]

        hash_cpu = (inner_rows + outer_rows) * self._cpu_operator_cost
        join_cpu = outer_rows * self._cpu_tuple_cost

        total_cost = build_cost + probe_cost + hash_cpu + join_cpu
        output_rows = max(1, int(outer_rows * inner_rows * join_selectivity))

        return {
            "strategy": "Hash Join",
            "outer_table": outer_cost.get("table", "derived"),
            "inner_table": inner_cost.get("table", "derived"),
            "total_cost": round(total_cost, 4),
            "output_rows": output_rows,
            "join_selectivity": join_selectivity,
            "build_cost": round(build_cost, 4),
            "probe_cost": round(probe_cost, 4)
        }

    def estimate_merge_join_cost(self, outer_cost: Dict, inner_cost: Dict,
                                  join_selectivity: float,
                                  outer_sorted: bool = False,
                                  inner_sorted: bool = False) -> Dict:
        """Estimate cost of a merge join with optional pre-sorting."""
        outer_rows = outer_cost["output_rows"]
        inner_rows = inner_cost["output_rows"]

        sort_cost_outer = 0.0
        if not outer_sorted and outer_rows > 1:
            sort_cost_outer = outer_rows * math.log2(max(outer_rows, 2)) * self._cpu_operator_cost

        sort_cost_inner = 0.0
        if not inner_sorted and inner_rows > 1:
            sort_cost_inner = inner_rows * math.log2(max(inner_rows, 2)) * self._cpu_operator_cost

        merge_cpu = (outer_rows + inner_rows) * self._cpu_tuple_cost
        total_cost = (outer_cost["total_cost"] + inner_cost["total_cost"] +
                      sort_cost_outer + sort_cost_inner + merge_cpu)

        output_rows = max(1, int(outer_rows * inner_rows * join_selectivity))

        return {
            "strategy": "Merge Join",
            "outer_table": outer_cost.get("table", "derived"),
            "inner_table": inner_cost.get("table", "derived"),
            "total_cost": round(total_cost, 4),
            "output_rows": output_rows,
            "join_selectivity": join_selectivity,
            "sort_cost_outer": round(sort_cost_outer, 4),
            "sort_cost_inner": round(sort_cost_inner, 4)
        }

    def compute_filter_selectivity(self, table_name: str, column_name: str,
                                    operator: str, value: str) -> float:
        """Compute selectivity estimate for a filter predicate."""
        col_stats = self._catalog.get_column_stats(table_name, column_name)
        if not col_stats:
            return 0.33

        n_distinct = col_stats.n_distinct
        null_fraction = col_stats.null_fraction

        if operator == '=':
            return (1.0 - null_fraction) / max(n_distinct, 1)
        elif operator in ('>', '<', '>=', '<='):
            return 0.33 * (1.0 - null_fraction)
        elif operator in ('!=', '<>'):
            return 1.0 - (1.0 - null_fraction) / max(n_distinct, 1)
        elif operator == 'LIKE':
            return 0.1
        else:
            return 0.25
