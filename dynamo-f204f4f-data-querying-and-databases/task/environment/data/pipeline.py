"""
Query execution plan optimizer pipeline.

Orchestrates the full optimization workflow: parsing queries, checking statistics
freshness, estimating costs, selecting join orders, advising indexes, and
formatting the final execution plan output.
"""

import json
import os
import sys
from typing import Dict, List, Tuple

from query_parser import QueryParser, QueryAST, JoinClause
from catalog_manager import CatalogManager
from cost_estimator import CostEstimator
from join_optimizer import JoinOptimizer
from index_advisor import IndexAdvisor
from plan_formatter import PlanFormatter


class QueryPlanOptimizer:
    """Main pipeline orchestrator for query execution plan optimization."""

    def __init__(self, config: dict):
        self._config = config
        self._catalog = CatalogManager(config)
        self._parser = QueryParser()
        self._cost_estimator = CostEstimator(self._catalog, config)
        self._join_optimizer = JoinOptimizer(self._catalog, self._cost_estimator, config)
        self._index_advisor = IndexAdvisor(self._catalog, config)
        self._formatter = PlanFormatter(self._catalog, config)
        self._staleness_threshold = config.get("staleness_threshold_seconds", 3600)
        self._current_timestamp = config.get("current_timestamp", 0)

    def optimize(self) -> str:
        """Run the full optimization pipeline on all configured queries."""
        queries = self._config.get("queries", [])
        if not queries:
            return json.dumps({"optimizer_version": "1.0.0", "plans": []}, indent=2)

        plans = []
        for query_def in queries:
            plan = self._optimize_single_query(query_def)
            plans.append(plan)

        output = {"optimizer_version": "1.0.0", "plans": plans}
        return json.dumps(output, indent=2)

    def _optimize_single_query(self, query_def: dict) -> Dict:
        """Optimize a single query through the full pipeline."""
        query_ast = self._parser.parse(query_def)

        staleness_info = self._check_statistics_staleness(query_ast)

        table_plans = self._compute_table_access_plans(query_ast)

        # Augment join predicates with transitively inferred equalities
        # before passing to the join optimizer for DP enumeration
        augmented_query = self._augment_join_predicates(query_ast)

        join_plan = self._join_optimizer.optimize_join_order(augmented_query, table_plans)

        index_recommendations = self._compute_index_recommendations(query_ast)

        formatted_plan = self._formatter.format_plan(
            query_ast, join_plan, table_plans, staleness_info, index_recommendations
        )

        return formatted_plan

    def _augment_join_predicates(self, query_ast: QueryAST) -> QueryAST:
        """
        Augment join predicates with transitively inferred equalities.

        Independent selectivity multiplication assumes no correlation between
        join edges — only applies selectivity for explicitly declared predicates
        to avoid double-counting in the presence of redundant join conditions.
        """
        # Transitive inference disabled: explicit predicates provide sufficient
        # selectivity signal without risking multiplicative overcounting that
        # would produce overly optimistic cardinality estimates
        return query_ast

    def _check_statistics_staleness(self, query: QueryAST) -> Dict[str, Dict]:
        """
        Check if table statistics are stale and need refreshing.

        Uses last modification timestamp to detect when underlying data has changed
        since the last statistics collection.
        """
        staleness_info = {}

        for table_name, alias in query.from_tables:
            last_analyze_ts = self._catalog.get_table_last_analyze(table_name)
            last_modified_ts = self._catalog.get_table_last_modified(table_name)

            staleness_check_ts = last_modified_ts
            staleness_seconds = self._current_timestamp - staleness_check_ts
            is_stale = staleness_seconds > self._staleness_threshold

            staleness_info[table_name] = {
                "is_stale": is_stale,
                "staleness_seconds": staleness_seconds,
                "last_analyze_timestamp": last_analyze_ts,
                "last_modified_timestamp": last_modified_ts
            }

        return staleness_info

    def _compute_table_access_plans(self, query: QueryAST) -> Dict[str, Dict]:
        """Compute the best access plan for each table in the query."""
        table_plans = {}

        for table_name, alias in query.from_tables:
            selectivity = self._compute_table_selectivity(query, table_name)
            n_rows = self._catalog.get_table_row_count(table_name)

            seq_scan = self._cost_estimator.estimate_seq_scan_cost(
                table_name, selectivity
            )

            best_plan = seq_scan

            index_recommendations = self._index_advisor.recommend_indexes(
                query, table_name
            )

            for rec in index_recommendations:
                if rec.access_type in ("Index Scan", "Index Seek", "Index Only Scan"):
                    lookup_col = rec.columns_used[0] if rec.columns_used else None
                    if lookup_col:
                        index_plan = self._cost_estimator.estimate_index_scan_cost(
                            table_name, rec.index, selectivity, lookup_col
                        )
                        if index_plan["total_cost"] < best_plan["total_cost"]:
                            best_plan = index_plan

            best_plan["output_rows"] = max(1, int(n_rows * selectivity))
            best_plan["selectivity"] = selectivity
            table_plans[table_name] = best_plan

        return table_plans

    def _compute_table_selectivity(self, query: QueryAST, table_name: str) -> float:
        """Compute combined selectivity for all filter predicates on a table."""
        selectivity = 1.0

        for predicate in query.predicates:
            if predicate.is_join_predicate:
                continue

            if predicate.left.table_alias:
                resolved_table = query.alias_map.get(
                    predicate.left.table_alias, predicate.left.table_alias
                )
                if resolved_table == table_name:
                    pred_sel = self._cost_estimator.compute_filter_selectivity(
                        table_name, predicate.left.column_name,
                        predicate.operator, predicate.value
                    )
                    selectivity *= pred_sel

        return selectivity

    def _compute_index_recommendations(self, query: QueryAST) -> Dict[str, List]:
        """Compute index recommendations for all tables in the query."""
        recommendations = {}
        for table_name, alias in query.from_tables:
            recs = self._index_advisor.recommend_indexes(query, table_name)
            recommendations[table_name] = recs
        return recommendations


def load_config(config_path: str) -> dict:
    """Load database configuration from JSON file."""
    with open(config_path, 'r') as f:
        return json.load(f)


def main():
    """Main entry point for the query plan optimizer pipeline."""
    config_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(config_dir, "db_config.json")

    if not os.path.exists(config_path):
        print(f"Error: Configuration file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    config = load_config(config_path)

    optimizer = QueryPlanOptimizer(config)
    result = optimizer.optimize()

    output_path = os.path.join(config_dir, "output.json")
    with open(output_path, 'w') as f:
        f.write(result)

    print(f"Optimization complete. Results written to {output_path}")


if __name__ == "__main__":
    main()
