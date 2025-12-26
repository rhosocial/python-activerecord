# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

SQLite is a lightweight database with limited support for advanced SQL features.
This dialect implements only the protocols for features that SQLite actually supports,
based on the SQLite version provided at initialization.
"""
from typing import Any, Dict, List, Optional, Tuple

from rhosocial.activerecord.backend.dialect import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.base import BaseDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport,
    ReturningSupport,
    JSONSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    WindowFunctionSupport
)
from rhosocial.activerecord.backend.expression.statements import MergeActionType, MergeAction, MergeExpression
from rhosocial.activerecord.backend.expression.advanced_functions import OrderedSetAggregation
from rhosocial.activerecord.backend.expression.graph import GraphVertex, GraphEdge, MatchClause, GraphEdgeDirection
from rhosocial.activerecord.backend.expression.query_sources import JSONTableColumn, JSONTableExpression
from rhosocial.activerecord.backend.expression.query_parts import LimitOffsetClause


class SQLiteDialect(
    BaseDialect,
    CTESupport,
    ReturningSupport,
    JSONSupport,
    FilterClauseSupport,
    OrderedSetAggregationSupport,
    MergeSupport,
    TemporalTableSupport,
    QualifyClauseSupport,
    LockingSupport,
    GraphSupport,
    WindowFunctionSupport
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

    def get_placeholder(self) -> str:
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

    def supports_ordered_set_aggregation(self) -> bool:
        """SQLite does not support ordered-set aggregate functions (WITHIN GROUP)."""
        return False

    def supports_merge_statement(self) -> bool:
        """SQLite does not support MERGE statements."""
        return False

    def supports_temporal_tables(self) -> bool:
        """SQLite does not support temporal table queries."""
        return False

    def supports_qualify_clause(self) -> bool:
        """SQLite does not support QUALIFY clause."""
        return False

    def supports_for_update_skip_locked(self) -> bool:
        """SQLite does not support FOR UPDATE/FOR SHARE with SKIP LOCKED."""
        return False

    def supports_graph_match(self) -> bool:
        """SQLite does not support graph query MATCH clause."""
        return False
    # endregion

    def format_returning_clause(
        self,
        columns: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format RETURNING clause for SQLite.

        Args:
            columns: List of column names

        Returns:
            Tuple of (SQL string, empty parameters tuple)
        """
        if not self.supports_returning_clause():
            raise UnsupportedFeatureError(
                self.name,
                "RETURNING clause",
                f"RETURNING clause requires SQLite 3.35.0+, current version is {'.'.join(map(str, self.version))}"
            )
        
        cols = [self.format_identifier(c) for c in columns]
        return f"RETURNING {', '.join(cols)}", ()

    def format_filter_clause(
        self,
        condition_sql: str,
        condition_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Format a FILTER (WHERE ...) clause.

        Args:
            condition_sql: SQL string for the WHERE condition.
            condition_params: Parameters for the WHERE condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        if not self.supports_filter_clause():
            raise UnsupportedFeatureError(
                self.name,
                "FILTER clause",
                f"FILTER clause requires SQLite 3.10.0+, current version is {'.'.join(map(str, self.version))}"
            )
        
        return f"FILTER (WHERE {condition_sql})", condition_params

    def format_limit_offset_clause(
        self,
        clause: "LimitOffsetClause"
    ) -> Tuple[str, tuple]:
        """
        Format LIMIT/OFFSET clause with SQLite-specific handling.

        SQLite requires LIMIT when using OFFSET alone, so we use LIMIT -1
        to indicate "no limit" when only OFFSET is specified.

        Args:
            clause: LimitOffsetClause object containing the limit and offset specifications.

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        # Check if we have offset but no limit, which needs special handling in SQLite
        if clause.offset is not None and clause.limit is None:
            return "LIMIT -1 OFFSET ?", (clause.offset,)
        # Otherwise, use the parent implementation
        return super().format_limit_offset_clause(clause)

    def format_json_table_expression(
        self,
        json_col_sql: str,
        path: str,
        columns: List[Dict[str, Any]],
        alias: Optional[str],
        params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a JSON_TABLE expression.

        SQLite does not support JSON_TABLE.
        """
        raise UnsupportedFeatureError(
            self.name,
            "JSON_TABLE function",
            "Consider using json_each() or json_extract() with subqueries or CTEs instead."
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
        Format an ordered-set aggregate function call.

        SQLite does not support ordered-set aggregate functions (WITHIN GROUP).
        """
        raise UnsupportedFeatureError(
            self.name,
            "Ordered-set aggregate functions (WITHIN GROUP)",
            "Consider emulating with window functions or subqueries if possible."
        )

    def format_merge_statement(
        self,
        target_sql: str,
        source_sql: str,
        on_sql: str,
        when_matched: List[Dict[str, Any]],
        when_not_matched: List[Dict[str, Any]],
        all_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a MERGE statement.

        SQLite does not support MERGE statements.
        """
        raise UnsupportedFeatureError(
            self.name,
            "MERGE statement",
            "Consider using a combination of INSERT, UPDATE, and DELETE statements."
        )

    def format_temporal_options(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a temporal table clause.

        SQLite does not support temporal tables.
        """
        raise UnsupportedFeatureError(
            self.name,
            "Temporal table queries (FOR SYSTEM_TIME)",
            "Manage historical data through application logic or custom versioning tables."
        )

    def format_qualify_clause(
        self,
        qualify_sql: str,
        qualify_params: tuple
    ) -> Tuple[str, Tuple]:
        """
        Formats a QUALIFY clause.

        SQLite does not support QUALIFY clause.
        """
        raise UnsupportedFeatureError(
            self.name,
            "QUALIFY clause",
            "Consider using a CTE or subquery with WHERE clause instead."
        )

    def format_for_update_clause(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE/FOR SHARE clause.

        SQLite does not support FOR UPDATE/FOR SHARE.
        """
        raise UnsupportedFeatureError(
            self.name,
            "FOR UPDATE / FOR SHARE clauses",
            "Implement locking at the application level or use transactions for atomicity."
        )

    def format_match_clause(
        self,
        path_sql: List[str],
        path_params: tuple
    ) -> Tuple[str, tuple]:
        """
        Formats a MATCH clause.

        SQLite does not support graph query MATCH clause.
        """
        raise UnsupportedFeatureError(
            self.name,
            "Graph query MATCH clause",
            "Implement graph traversal logic in application code or use a graph database."
        )