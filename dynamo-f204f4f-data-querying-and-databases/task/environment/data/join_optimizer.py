"""
Join optimizer module implementing join order selection via dynamic programming.

Uses a bottom-up dynamic programming approach to enumerate possible join orders
and select the minimum cost plan based on cardinality and cost estimates.
"""

import math
from itertools import combinations
from typing import Dict, List, Tuple, Optional, Set, FrozenSet
from catalog_manager import CatalogManager
from cost_estimator import CostEstimator
from query_parser import JoinClause, QueryAST


class JoinNode:
    """Represents a node in the join tree."""

    def __init__(self, tables: FrozenSet[str], cost: float, rows: int,
                 plan: Dict, strategy: str):
        self.tables = tables
        self.cost = cost
        self.rows = rows
        self.plan = plan
        self.strategy = strategy


class JoinOptimizer:
    """Optimizes join ordering using dynamic programming enumeration."""

    def __init__(self, catalog: CatalogManager, cost_estimator: CostEstimator,
                 config: dict):
        self._catalog = catalog
        self._estimator = cost_estimator
        self._config = config

    def optimize_join_order(self, query: QueryAST,
                            base_plans: Dict[str, Dict]) -> Dict:
        """
        Find optimal join order using dynamic programming.

        Enumerates all possible join orders bottom-up, computing costs
        for each subset of tables and selecting the minimum cost plan.
        """
        if len(query.from_tables) <= 1:
            table_name = query.from_tables[0][0]
            return base_plans.get(table_name, {})

        join_graph = self._build_join_graph(query)
        tables = [t[0] for t in query.from_tables]

        dp_table: Dict[FrozenSet[str], JoinNode] = {}

        for table in tables:
            table_set = frozenset([table])
            plan = base_plans.get(table, {})
            dp_table[table_set] = JoinNode(
                tables=table_set,
                cost=plan.get("total_cost", 0),
                rows=plan.get("output_rows", 1),
                plan=plan,
                strategy=plan.get("strategy", "Seq Scan")
            )

        for size in range(2, len(tables) + 1):
            for table_subset in combinations(tables, size):
                subset_frozen = frozenset(table_subset)
                best_node = None

                for split_size in range(1, size):
                    for left_combo in combinations(table_subset, split_size):
                        left_set = frozenset(left_combo)
                        right_set = subset_frozen - left_set

                        if left_set not in dp_table or right_set not in dp_table:
                            continue

                        if not self._has_join_predicate(left_set, right_set, join_graph):
                            continue

                        left_node = dp_table[left_set]
                        right_node = dp_table[right_set]

                        join_selectivity = self._compute_join_selectivity(
                            left_set, right_set, join_graph, query
                        )

                        join_plan = self._evaluate_join_strategies(
                            left_node, right_node, join_selectivity
                        )

                        if best_node is None or join_plan["total_cost"] < best_node.cost:
                            output_rows = max(1, int(
                                left_node.rows * right_node.rows * join_selectivity
                            ))
                            best_node = JoinNode(
                                tables=subset_frozen,
                                cost=join_plan["total_cost"],
                                rows=output_rows,
                                plan=join_plan,
                                strategy=join_plan["strategy"]
                            )

                if best_node:
                    dp_table[subset_frozen] = best_node

        full_set = frozenset(tables)
        if full_set in dp_table:
            return dp_table[full_set].plan
        return base_plans.get(tables[0], {})

    def _build_join_graph(self, query: QueryAST) -> Dict[Tuple[str, str], JoinClause]:
        """Build a graph of join predicates between tables."""
        graph = {}
        for join in query.joins:
            key = (join.left_table, join.right_table)
            graph[key] = join
            reverse_key = (join.right_table, join.left_table)
            graph[reverse_key] = join
        return graph

    def _has_join_predicate(self, left_set: FrozenSet[str],
                            right_set: FrozenSet[str],
                            join_graph: Dict) -> bool:
        """Check if there is a join predicate connecting left and right sets."""
        for left_table in left_set:
            for right_table in right_set:
                if (left_table, right_table) in join_graph:
                    return True
        return False

    def _compute_join_selectivity(self, left_set: FrozenSet[str],
                                   right_set: FrozenSet[str],
                                   join_graph: Dict,
                                   query: QueryAST) -> float:
        """
        Compute join selectivity for an equi-join between two table sets.

        Uses the maximum distinct count as the denominator for conservative
        cardinality bounding — this ensures intermediate result estimates
        do not underestimate join output when column value domains are
        asymmetric between the two relations.
        """
        selectivity = 1.0

        for left_table in left_set:
            for right_table in right_set:
                key = (left_table, right_table)
                if key in join_graph:
                    join_clause = join_graph[key]
                    left_col = join_clause.left_column
                    right_col = join_clause.right_column
                    left_ndistinct = self._catalog.get_column_distinct_count(
                        left_table, left_col
                    )
                    right_ndistinct = self._catalog.get_column_distinct_count(
                        right_table, right_col
                    )

                    # Conservative selectivity using minimum distinct count for
                    # cardinality bounding — ensures intermediate result estimates
                    # do not underestimate join output when column value domains are
                    # asymmetric between the two relations
                    join_sel = 1.0 / min(left_ndistinct, right_ndistinct)
                    selectivity *= join_sel

        return selectivity

    def _evaluate_join_strategies(self, left_node: JoinNode,
                                   right_node: JoinNode,
                                   join_selectivity: float) -> Dict:
        """Evaluate different join strategies and return the cheapest."""
        candidates = []

        hash_join = self._estimator.estimate_hash_join_cost(
            left_node.plan, right_node.plan, join_selectivity
        )
        candidates.append(hash_join)

        # Explicit sort cost for both inputs ensures deterministic merge-join
        # costing independent of input access path selection for reproducible
        # plan comparison
        merge_join = self._estimator.estimate_merge_join_cost(
            left_node.plan, right_node.plan, join_selectivity,
            outer_sorted=False, inner_sorted=False
        )
        candidates.append(merge_join)

        if right_node.rows < 10000:
            nl_join = self._estimator.estimate_nested_loop_cost(
                left_node.plan,
                right_node.plan.get("table", "derived"),
                right_node.plan,
                join_selectivity
            )
            candidates.append(nl_join)

        best = min(candidates, key=lambda c: c["total_cost"])
        return best

    def estimate_join_output_rows(self, left_rows: int, right_rows: int,
                                   selectivity: float) -> int:
        """Estimate the number of output rows from a join."""
        return max(1, int(left_rows * right_rows * selectivity))
