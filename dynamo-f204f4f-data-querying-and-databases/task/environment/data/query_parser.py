"""
Query parser module for SQL-like query parsing into AST nodes.

Parses structured query definitions from the configuration into an internal
abstract syntax tree representation suitable for cost estimation and optimization.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple


@dataclass
class ColumnRef:
    """Reference to a column, optionally qualified with a table alias."""
    table_alias: Optional[str]
    column_name: str

    def qualified_name(self) -> str:
        if self.table_alias:
            return f"{self.table_alias}.{self.column_name}"
        return self.column_name


@dataclass
class Predicate:
    """A filter predicate in a WHERE clause."""
    left: ColumnRef
    operator: str
    value: str
    is_join_predicate: bool = False
    right: Optional[ColumnRef] = None


@dataclass
class JoinClause:
    """Represents a JOIN between two tables."""
    left_table: str
    right_table: str
    left_alias: str
    right_alias: str
    left_column: str
    right_column: str
    join_type: str = "INNER"


@dataclass
class SelectColumn:
    """A column in the SELECT list."""
    table_alias: Optional[str]
    column_name: str
    output_alias: Optional[str] = None


@dataclass
class QueryAST:
    """Abstract syntax tree representation of a parsed query."""
    select_columns: List[SelectColumn]
    from_tables: List[Tuple[str, str]]
    joins: List[JoinClause]
    predicates: List[Predicate]
    alias_map: Dict[str, str]
    original_sql: str


class QueryParser:
    """Parses SQL query definitions into AST node structures."""

    def __init__(self):
        self._operator_pattern = re.compile(r'(>=|<=|!=|<>|=|>|<|LIKE|IN|IS)')
        self._supported_join_types = {"INNER", "LEFT", "RIGHT", "FULL", "CROSS"}

    def parse(self, query_def: dict) -> QueryAST:
        """Parse a query definition dictionary into a QueryAST."""
        sql = query_def["sql"]
        alias_map = query_def.get("alias_map", {})

        select_columns = self._parse_select(sql, alias_map)
        from_tables = self._parse_from(sql, alias_map)
        joins = self._parse_joins(sql, alias_map)
        predicates = self._parse_where(sql, alias_map)

        return QueryAST(
            select_columns=select_columns,
            from_tables=from_tables,
            joins=joins,
            predicates=predicates,
            alias_map=alias_map,
            original_sql=sql
        )

    def _parse_select(self, sql: str, alias_map: dict) -> List[SelectColumn]:
        """Extract SELECT column list from SQL string."""
        select_match = re.search(r'SELECT\s+(.+?)\s+FROM', sql, re.IGNORECASE)
        if not select_match:
            return []

        columns_str = select_match.group(1)
        columns = []

        for col_expr in columns_str.split(','):
            col_expr = col_expr.strip()
            parts = col_expr.split('.')
            if len(parts) == 2:
                table_alias = parts[0].strip()
                col_name = parts[1].strip()
                columns.append(SelectColumn(
                    table_alias=table_alias,
                    column_name=col_name
                ))
            else:
                columns.append(SelectColumn(
                    table_alias=None,
                    column_name=parts[0].strip()
                ))

        return columns

    def _parse_from(self, sql: str, alias_map: dict) -> List[Tuple[str, str]]:
        """Extract FROM clause tables with their aliases."""
        tables = []
        for alias, table_name in alias_map.items():
            tables.append((table_name, alias))
        return tables

    def _parse_joins(self, sql: str, alias_map: dict) -> List[JoinClause]:
        """Extract JOIN clauses from SQL string."""
        joins = []
        join_pattern = re.compile(
            r'JOIN\s+(\w+)\s+(\w+)\s+ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)',
            re.IGNORECASE
        )

        for match in join_pattern.finditer(sql):
            right_table = match.group(1)
            right_alias = match.group(2)
            left_alias = match.group(3)
            left_col = match.group(4)
            right_alias_ref = match.group(5)
            right_col = match.group(6)

            left_table = alias_map.get(left_alias, left_alias)
            right_table_resolved = alias_map.get(right_alias, right_table)

            joins.append(JoinClause(
                left_table=left_table,
                right_table=right_table_resolved,
                left_alias=left_alias,
                right_alias=right_alias_ref,
                left_column=left_col,
                right_column=right_col
            ))

        return joins

    def _parse_where(self, sql: str, alias_map: dict) -> List[Predicate]:
        """Extract WHERE clause predicates from SQL string."""
        predicates = []
        where_match = re.search(r'WHERE\s+(.+?)(?:ORDER|GROUP|HAVING|LIMIT|$)',
                                sql, re.IGNORECASE)
        if not where_match:
            return []

        where_str = where_match.group(1).strip()
        conditions = re.split(r'\s+AND\s+', where_str, flags=re.IGNORECASE)

        for condition in conditions:
            condition = condition.strip()
            predicate = self._parse_condition(condition, alias_map)
            if predicate:
                predicates.append(predicate)

        return predicates

    def _parse_condition(self, condition: str, alias_map: dict) -> Optional[Predicate]:
        """Parse a single condition into a Predicate node."""
        op_match = self._operator_pattern.search(condition)
        if not op_match:
            return None

        operator = op_match.group(1)
        left_str = condition[:op_match.start()].strip()
        right_str = condition[op_match.end():].strip()

        left_col = self._parse_column_ref(left_str)
        if not left_col:
            return None

        right_col = self._parse_column_ref(right_str)
        if right_col and right_col.table_alias in alias_map:
            return Predicate(
                left=left_col,
                operator=operator,
                value=right_str,
                is_join_predicate=True,
                right=right_col
            )

        return Predicate(
            left=left_col,
            operator=operator,
            value=right_str.strip("'\""),
            is_join_predicate=False
        )

    def _parse_column_ref(self, ref_str: str) -> Optional[ColumnRef]:
        """Parse a column reference string into a ColumnRef node."""
        parts = ref_str.split('.')
        if len(parts) == 2:
            return ColumnRef(table_alias=parts[0].strip(), column_name=parts[1].strip())
        elif len(parts) == 1 and parts[0].isidentifier():
            return ColumnRef(table_alias=None, column_name=parts[0].strip())
        return None
