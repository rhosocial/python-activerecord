# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

This dialect implements only the protocols for features that SQLite actually supports,
based on the SQLite version provided at initialization.
"""
from typing import Any, Dict, List, Optional, Tuple, Union

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    JSONSupport,
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
    LockingSupport,
    MergeSupport,
    OrderedSetAggregationSupport,
    QualifyClauseSupport,
    TemporalTableSupport,
    UpsertSupport,
    LateralJoinSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CTEMixin,
    FilterClauseMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin,
    AdvancedGroupingMixin,
    ArrayMixin,
    ExplainMixin,
    GraphMixin,
    LockingMixin,
    MergeMixin,
    OrderedSetAggregationMixin,
    QualifyClauseMixin,
    TemporalTableMixin,
    UpsertMixin,
    LateralJoinMixin,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError


class SQLiteDialect(
    SQLDialectBase,
    # Include mixins for features that SQLite supports (with version-dependent implementations)
    CTEMixin,
    FilterClauseMixin,
    WindowFunctionMixin,
    JSONMixin,
    ReturningMixin,
    # Include mixins for features that SQLite does NOT support but need the methods to exist
    AdvancedGroupingMixin,
    ArrayMixin,
    ExplainMixin,
    GraphMixin,
    LockingMixin,
    MergeMixin,
    OrderedSetAggregationMixin,
    QualifyClauseMixin,
    TemporalTableMixin,
    UpsertMixin,
    LateralJoinMixin,
    # Protocols for type checking
    CTESupport,
    FilterClauseSupport,
    WindowFunctionSupport,
    JSONSupport,
    ReturningSupport,
    AdvancedGroupingSupport,
    ArraySupport,
    ExplainSupport,
    GraphSupport,
    LockingSupport,
    MergeSupport,
    OrderedSetAggregationSupport,
    QualifyClauseSupport,
    TemporalTableSupport,
    UpsertSupport,
    LateralJoinSupport,
):
    """
    SQLite dialect implementation that adapts to the SQLite version.

    SQLite features and support based on version:
    - Basic and recursive CTEs (since 3.8.3)
    - Window functions (since 3.25.0)
    - RETURNING clause (since 3.35.0)
    - JSON operations (with JSON1 extension, since 3.38.0)
    - FILTER clause (since 3.10.0)
    """

    def __init__(self, version: Tuple[int, int, int] = (3, 35, 0)):
        """
        Initialize SQLite dialect with specific version.

        Args:
            version: SQLite version tuple (major, minor, patch)
        """
        self.version = version
        super().__init__()

    def get_parameter_placeholder(self, position: int = 0) -> str:
        """SQLite uses '?' for placeholders."""
        return "?"

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the SQLite version this dialect is configured for."""
        return self.version

    # region Protocol Support Checks based on version
    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since SQLite 3.8.3."""
        return self.version >= (3, 8, 3)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since SQLite 3.8.3."""
        return self.version >= (3, 8, 3)

    def supports_materialized_cte(self) -> bool:
        """SQLite does not support MATERIALIZED hint."""
        return False

    def supports_returning_clause(self) -> bool:
        """RETURNING clause is supported since SQLite 3.35.0."""
        return self.version >= (3, 35, 0)

    def supports_window_functions(self) -> bool:
        """Window functions are supported since SQLite 3.25.0."""
        return self.version >= (3, 25, 0)

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported, since SQLite 3.25.0."""
        return self.version >= (3, 25, 0)

    def supports_filter_clause(self) -> bool:
        """FILTER clause for aggregate functions is supported since SQLite 3.10.0."""
        return self.version >= (3, 10, 0)

    def supports_json_type(self) -> bool:
        """JSON is supported with JSON1 extension."""
        return self.version >= (3, 38, 0)  # JSON1 extension available since 3.38.0

    def get_json_access_operator(self) -> str:
        """SQLite uses '->' for JSON access."""
        return "->"

    def supports_json_table(self) -> bool:
        """SQLite does not directly support JSON_TABLE as a table function."""
        return False
    # endregion

    # region Custom Implementations for SQLite-specific behavior
    def format_identifier(self, identifier: str) -> str:
        """
        Format identifier using SQLite's double quote quoting mechanism.

        Args:
            identifier: Raw identifier string

        Returns:
            Quoted identifier with escaped internal quotes
        """
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def format_join_expression(
        self,
        join_expr: "JoinExpression"
    ) -> Tuple[str, Tuple]:
        """
        Format JOIN expression with SQLite-specific limitations.

        SQLite does not support RIGHT JOIN or FULL OUTER JOIN.
        """
        # Check if the join type is supported by SQLite
        join_type_upper = join_expr.join_type.upper()
        if "RIGHT" in join_type_upper or "FULL" in join_type_upper:
            raise UnsupportedFeatureError(
                self.name,
                join_expr.join_type,
                "SQLite does not support RIGHT JOIN or FULL OUTER JOIN"
            )

        # Delegate to parent implementation (from mixin) for supported joins
        return super().format_join_expression(join_expr)

    # Additional protocol support methods for features SQLite doesn't support
    def supports_rollup(self) -> bool:
        """SQLite does not support ROLLUP."""
        return False

    def supports_cube(self) -> bool:
        """SQLite does not support CUBE."""
        return False

    def supports_grouping_sets(self) -> bool:
        """SQLite does not support GROUPING SETS."""
        return False

    def supports_array_type(self) -> bool:
        """SQLite does not support native array types."""
        return False

    def supports_array_constructor(self) -> bool:
        """SQLite does not support ARRAY constructor."""
        return False

    def supports_array_access(self) -> bool:
        """SQLite does not support array subscript access."""
        return False

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        # SQLite supports EXPLAIN but not necessarily ANALYZE depending on version/config
        # For simplicity, we'll say it's supported
        return True

    def supports_explain_format(self, format_type: str) -> bool:
        """Check if specific EXPLAIN format is supported."""
        # SQLite has limited support for different EXPLAIN formats
        return format_type.upper() in ["TEXT", "DOT"]

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        return False

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        return False

    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        return False

    def supports_temporal_tables(self) -> bool:
        """Whether temporal tables are supported."""
        return False

    def supports_qualify_clause(self) -> bool:
        """Whether QUALIFY clause is supported."""
        return False

    def supports_upsert(self) -> bool:
        """Whether UPSERT (ON CONFLICT) is supported."""
        # UPSERT (ON CONFLICT) is supported since SQLite 3.24.0
        return self.version >= (3, 24, 0)

    def get_upsert_syntax_type(self) -> str:
        """
        Get UPSERT syntax type.

        Returns:
            'ON CONFLICT' (PostgreSQL/SQLite) or 'ON DUPLICATE KEY' (MySQL)
        """
        return "ON CONFLICT"

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        # LATERAL joins are supported in SQLite
        return True

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        return False

    def format_grouping_expression(
        self,
        operation: str,
        expressions: List["bases.BaseExpression"]
    ) -> Tuple[str, tuple]:
        """Format grouping expression (ROLLUP, CUBE, GROUPING SETS)."""
        # Check feature support based on operation type
        if operation.upper() == "ROLLUP":
            if not self.supports_rollup():
                raise UnsupportedFeatureError(self.name, "ROLLUP")
        elif operation.upper() == "CUBE":
            if not self.supports_cube():
                raise UnsupportedFeatureError(self.name, "CUBE")
        elif operation.upper() == "GROUPING SETS":
            if not self.supports_grouping_sets():
                raise UnsupportedFeatureError(self.name, "GROUPING SETS")

        # Since SQLite doesn't support these operations, raise an error
        raise UnsupportedFeatureError(
            self.name,
            f"{operation} grouping operation",
            f"{operation} is not supported by SQLite."
        )

    def format_array_expression(
        self,
        operation: str,
        elements: Optional[List["bases.BaseExpression"]],
        base_expr: Optional["bases.BaseExpression"],
        index_expr: Optional["bases.BaseExpression"]
    ) -> Tuple[str, Tuple]:
        """Format array expression."""
        # SQLite does not support native array types
        raise UnsupportedFeatureError(
            self.name,
            "Array operations",
            "SQLite does not support native array types. Consider using JSON or comma-separated values."
        )

    def format_json_table_expression(
        self,
        json_col_sql: str,
        path: str,
        columns: List[Dict[str, Any]],
        alias: Optional[str],
        params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format JSON_TABLE expression.

        Args:
            json_col_sql: SQL for the JSON column/expression.
            path: The JSON path expression.
            columns: A list of dictionaries, each defining a column.
            alias: The alias for the resulting table.
            params: Parameters for the JSON column expression.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        # SQLite does not support JSON_TABLE function directly
        raise UnsupportedFeatureError(
            self.name,
            "JSON_TABLE function",
            "SQLite does not support JSON_TABLE. Consider using json_each() or json_extract() with subqueries."
        )

    def format_match_clause(
        self,
        clause: "MatchClause"
    ) -> Tuple[str, tuple]:
        """
        Format MATCH clause with expression.

        Args:
            clause: MatchClause object containing the match expression

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        # SQLite does not support graph MATCH clause
        raise UnsupportedFeatureError(
            self.name,
            "graph MATCH clause",
            "SQLite does not support graph MATCH clause."
        )

    def format_ordered_set_aggregation(
        self,
        func_name: str,
        func_args_sql: List[str],
        func_args_params: tuple,
        order_by_sql: List[str],
        order_by_params: tuple,
        alias: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """
        Format ordered-set aggregation function call.

        Args:
            func_name: The name of the aggregate function.
            func_args_sql: List of SQL strings for the function's arguments.
            func_args_params: Parameters for the function's arguments.
            order_by_sql: List of SQL strings for the ORDER BY expressions.
            order_by_params: Parameters for the ORDER BY expressions.
            alias: Optional alias for the result.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        # SQLite does not support ordered-set aggregate functions
        raise UnsupportedFeatureError(
            self.name,
            "ordered-set aggregate functions",
            "SQLite does not support ordered-set aggregate functions (WITHIN GROUP)."
        )

    def format_qualify_clause(
        self,
        clause: "QualifyClause"
    ) -> Tuple[str, tuple]:
        """Format QUALIFY clause."""
        # SQLite does not support QUALIFY clause
        raise UnsupportedFeatureError(
            self.name,
            "QUALIFY clause",
            "SQLite does not support QUALIFY clause. Use a subquery or CTE instead."
        )

    def format_returning_clause(
        self,
        clause: "ReturningClause"
    ) -> Tuple[str, tuple]:
        """Format RETURNING clause."""
        # Check if the dialect supports returning clause
        if not self.supports_returning_clause():
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                "Use a separate SELECT statement to retrieve the affected data."
            )

        all_params = []
        expr_parts = []
        for expr in clause.expressions:
            expr_sql, expr_params = expr.to_sql()
            expr_parts.append(expr_sql)
            all_params.extend(expr_params)

        returning_sql = f"RETURNING {', '.join(expr_parts)}"

        # Add alias if provided
        if clause.alias:
            returning_sql += f" AS {self.format_identifier(clause.alias)}"

        return returning_sql, tuple(all_params)
    # endregion