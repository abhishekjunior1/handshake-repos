"""
Plan formatter module for execution plan output formatting.

Formats optimized query execution plans into structured JSON output
suitable for analysis and comparison.
"""

import json
from typing import Dict, List, Optional, Any
from query_parser import QueryAST
from catalog_manager import CatalogManager


class PlanFormatter:
    """Formats query execution plans into structured output."""

    def __init__(self, catalog: CatalogManager, config: dict):
        self._catalog = catalog
        self._config = config
        self._database = config.get("database", "unknown")

    def format_plan(self, query: QueryAST, join_plan: Dict,
                    table_plans: Dict[str, Dict],
                    staleness_info: Dict[str, Dict],
                    index_recommendations: Dict[str, List]) -> Dict:
        """Format a complete execution plan with all components."""
        plan = {
            "database": self._database,
            "query": query.original_sql,
            "plan_summary": self._format_summary(join_plan, table_plans),
            "scan_plans": self._format_scan_plans(table_plans),
            "join_plan": self._format_join_plan(join_plan),
            "statistics_status": self._format_staleness(staleness_info),
            "index_analysis": self._format_index_analysis(index_recommendations),
            "cost_breakdown": self._format_cost_breakdown(join_plan, table_plans),
            "optimization_notes": self._generate_notes(
                join_plan, table_plans, staleness_info
            )
        }
        return plan

    def _format_summary(self, join_plan: Dict, table_plans: Dict[str, Dict]) -> Dict:
        """Format high-level plan summary."""
        total_cost = join_plan.get("total_cost", 0)
        output_rows = join_plan.get("output_rows", 0)
        strategy = join_plan.get("strategy", "Unknown")

        table_strategies = {}
        for table, plan in table_plans.items():
            table_strategies[table] = plan.get("strategy", "Sequential Scan")

        return {
            "total_estimated_cost": total_cost,
            "estimated_output_rows": output_rows,
            "join_strategy": strategy,
            "table_access_strategies": table_strategies
        }

    def _format_scan_plans(self, table_plans: Dict[str, Dict]) -> List[Dict]:
        """Format individual table scan plans."""
        formatted = []
        for table_name, plan in sorted(table_plans.items()):
            entry = {
                "table": table_name,
                "strategy": plan.get("strategy", "Sequential Scan"),
                "io_cost": plan.get("io_cost", 0),
                "cpu_cost": plan.get("cpu_cost", 0),
                "total_cost": plan.get("total_cost", 0),
                "output_rows": plan.get("output_rows", 0),
                "selectivity": plan.get("selectivity", 1.0)
            }
            if "index" in plan:
                entry["index_used"] = plan["index"]
            if "correlation" in plan:
                entry["correlation"] = plan["correlation"]
            formatted.append(entry)
        return formatted

    def _format_join_plan(self, join_plan: Dict) -> Dict:
        """Format the join plan details."""
        formatted = {
            "strategy": join_plan.get("strategy", "Unknown"),
            "total_cost": join_plan.get("total_cost", 0),
            "output_rows": join_plan.get("output_rows", 0),
            "join_selectivity": join_plan.get("join_selectivity", 0)
        }

        if "outer_table" in join_plan:
            formatted["outer_table"] = join_plan["outer_table"]
        if "inner_table" in join_plan:
            formatted["inner_table"] = join_plan["inner_table"]
        if "build_cost" in join_plan:
            formatted["build_cost"] = join_plan["build_cost"]
        if "probe_cost" in join_plan:
            formatted["probe_cost"] = join_plan["probe_cost"]
        if "sort_cost_outer" in join_plan:
            formatted["sort_cost_outer"] = join_plan["sort_cost_outer"]
        if "sort_cost_inner" in join_plan:
            formatted["sort_cost_inner"] = join_plan["sort_cost_inner"]

        return formatted

    def _format_staleness(self, staleness_info: Dict[str, Dict]) -> Dict:
        """Format statistics staleness information."""
        formatted = {}
        for table, info in sorted(staleness_info.items()):
            formatted[table] = {
                "is_stale": info.get("is_stale", False),
                "staleness_seconds": info.get("staleness_seconds", 0),
                "recommendation": "ANALYZE recommended" if info.get("is_stale") else "Statistics current"
            }
        return formatted

    def _format_index_analysis(self, index_recommendations: Dict[str, List]) -> Dict:
        """Format index analysis results."""
        formatted = {}
        for table, recommendations in sorted(index_recommendations.items()):
            table_recs = []
            for rec in recommendations:
                table_recs.append({
                    "index_name": rec.index.name,
                    "access_type": rec.access_type,
                    "benefit_score": rec.benefit_score,
                    "columns": rec.columns_used
                })
            formatted[table] = table_recs
        return formatted

    def _format_cost_breakdown(self, join_plan: Dict,
                                table_plans: Dict[str, Dict]) -> Dict:
        """Format detailed cost breakdown."""
        total_scan_cost = sum(p.get("total_cost", 0) for p in table_plans.values())
        join_overhead = join_plan.get("total_cost", 0) - total_scan_cost

        return {
            "total_scan_cost": round(total_scan_cost, 4),
            "join_overhead": round(max(0, join_overhead), 4),
            "total_plan_cost": join_plan.get("total_cost", 0),
            "per_table_costs": {
                table: plan.get("total_cost", 0)
                for table, plan in sorted(table_plans.items())
            }
        }

    def _generate_notes(self, join_plan: Dict, table_plans: Dict[str, Dict],
                         staleness_info: Dict[str, Dict]) -> List[str]:
        """Generate optimization advisory notes."""
        notes = []

        stale_tables = [t for t, info in staleness_info.items()
                        if info.get("is_stale")]
        if stale_tables:
            notes.append(
                f"Statistics are stale for: {', '.join(sorted(stale_tables))}. "
                f"Consider running ANALYZE."
            )

        for table, plan in table_plans.items():
            if plan.get("strategy") == "Sequential Scan" and plan.get("selectivity", 1.0) < 0.1:
                notes.append(
                    f"Low selectivity scan on {table} "
                    f"({plan.get('selectivity', 0):.4f}): index may help."
                )

        if not notes:
            notes.append("Plan appears optimal for current statistics.")

        return notes

    def format_output(self, plans: List[Dict]) -> str:
        """Format all query plans into final JSON output string."""
        output = {
            "optimizer_version": "1.0.0",
            "plans": plans
        }
        return json.dumps(output, indent=2)
