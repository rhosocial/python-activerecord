# src/rhosocial/activerecord/backend/dialect/protocols.py
"""
SQL dialect protocol definitions.

This module defines protocol interfaces that dialects can implement to declare
support for advanced database features. Protocols enable fine-grained feature
detection and graceful error handling.
"""
from typing import Any, Dict, List, Optional, Tuple, Protocol, runtime_checkable, TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no cover
    from ..expression import bases, graph
    from ..expression.graph import GraphEdgeDirection


@runtime_checkable
class WindowFunctionSupport(Protocol):
    """Protocol for window function support."""

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported."""
        ...  # pragma: no cover

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported."""
        ...  # pragma: no cover


@runtime_checkable
class CTESupport(Protocol):
    """Protocol for Common Table Expression (CTE) support."""

    def supports_basic_cte(self) -> bool:
        """Whether basic CTEs are supported."""
        ...  # pragma: no cover

    def supports_recursive_cte(self) -> bool:
        """Whether recursive CTEs are supported."""
        ...  # pragma: no cover

    def supports_materialized_cte(self) -> bool:
        """Whether MATERIALIZED hint is supported."""
        ...  # pragma: no cover


@runtime_checkable
class AdvancedGroupingSupport(Protocol):
    """Protocol for advanced grouping operations (ROLLUP, CUBE, GROUPING SETS)."""

    def supports_rollup(self) -> bool:
        """Whether ROLLUP is supported."""
        ...  # pragma: no cover

    def supports_cube(self) -> bool:
        """Whether CUBE is supported."""
        ...  # pragma: no cover

    def supports_grouping_sets(self) -> bool:
        """Whether GROUPING SETS are supported."""
        ...  # pragma: no cover

    def format_grouping_expression(
        self,
        operation: str,
        expressions: List["bases.BaseExpression"]
    ) -> Tuple[str, tuple]:
        """
        Formats a grouping expression (ROLLUP, CUBE, GROUPING SETS).

        Args:
            operation: The grouping operation ('ROLLUP', 'CUBE', or 'GROUPING SETS').
            expressions: List of expressions to group by.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover


@runtime_checkable
class ReturningSupport(Protocol):
    """Protocol for RETURNING clause support."""

    def supports_returning_clause(self) -> bool:
        """Whether RETURNING clause is supported."""
        ...  # pragma: no cover

    def format_returning_clause(
            self,
            columns: List[str]
    ) -> Tuple[str, Tuple]:
        """
        Format a RETURNING clause.

        Args:
            columns: List of column names to return

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover


@runtime_checkable
class UpsertSupport(Protocol):
    """Protocol for UPSERT operation support."""

    def supports_upsert(self) -> bool:
        """Whether UPSERT is supported."""
        ...  # pragma: no cover

    def get_upsert_syntax_type(self) -> str:
        """
        Get UPSERT syntax type.

        Returns:
            'ON CONFLICT' (PostgreSQL) or 'ON DUPLICATE KEY' (MySQL)
        """
        ...  # pragma: no cover


@runtime_checkable
class LateralJoinSupport(Protocol):
    """Protocol for LATERAL join support."""

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        ...  # pragma: no cover


@runtime_checkable
class ArraySupport(Protocol):
    """Protocol for array type support."""

    def supports_array_type(self) -> bool:
        """Whether array types are supported."""
        ...  # pragma: no cover

    def supports_array_constructor(self) -> bool:
        """Whether ARRAY constructor is supported."""
        ...  # pragma: no cover

    def supports_array_access(self) -> bool:
        """Whether array subscript access is supported."""
        ...  # pragma: no cover


@runtime_checkable
class JSONSupport(Protocol):
    """Protocol for JSON type support."""

    def supports_json_type(self) -> bool:
        """Whether JSON type is supported."""
        ...  # pragma: no cover

    def get_json_access_operator(self) -> str:
        """
        Get JSON access operator.

        Returns:
            '->' (PostgreSQL/MySQL/SQLite) or other dialect-specific operator
        """
        ...  # pragma: no cover

    def supports_json_table(self) -> bool:
        """Whether JSON_TABLE function is supported."""
        ...  # pragma: no cover

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

        Args:
            json_col_sql: SQL for the JSON column/expression.
            path: The JSON path expression.
            columns: A list of dictionaries, each defining a column.
            alias: The alias for the resulting table.
            params: Parameters for the JSON column expression.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover


@runtime_checkable
class ExplainSupport(Protocol):
    """Protocol for EXPLAIN statement support."""

    def supports_explain_analyze(self) -> bool:
        """Whether EXPLAIN ANALYZE is supported."""
        ...  # pragma: no cover

    def supports_explain_format(self, format_type: str) -> bool:
        """
        Check if specific EXPLAIN format is supported.

        Args:
            format_type: Format type (e.g., 'JSON', 'XML', 'YAML')

        Returns:
            True if format is supported
        """
        ...  # pragma: no cover


@runtime_checkable
class GraphSupport(Protocol):
    """Protocol for graph query (MATCH) support."""

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        ...  # pragma: no cover

    def format_graph_vertex(
        self,
        variable: str,
        table: str
    ) -> Tuple[str, tuple]:
        """
        Formats a graph vertex expression.

        Args:
            variable: The vertex variable name.
            table: The vertex table name.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_graph_edge(
        self,
        variable: str,
        table: str,
        direction: "GraphEdgeDirection"
    ) -> Tuple[str, tuple]:
        """
        Formats a graph edge expression.

        Args:
            variable: The edge variable name.
            table: The edge table name.
            direction: The edge direction.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_match_clause(
        self,
        clause: "graph.MatchClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a MATCH clause.

        Args:
            clause: MatchClause object containing the match expression

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover


@runtime_checkable
class FilterClauseSupport(Protocol):
    """Protocol for aggregate FILTER clause support."""

    def supports_filter_clause(self) -> bool:
        """Whether FILTER (WHERE ...) clause is supported in aggregate functions."""
        ...  # pragma: no cover

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
        ...  # pragma: no cover


@runtime_checkable
class OrderedSetAggregationSupport(Protocol):
    """Protocol for ordered-set aggregate function support (WITHIN GROUP (ORDER BY ...))."""

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        ...  # pragma: no cover

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
        Formats an ordered-set aggregate function call.

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
        ...  # pragma: no cover


@runtime_checkable
class MergeSupport(Protocol):
    """Protocol for MERGE statement support."""

    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        ...  # pragma: no cover

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

        Args:
            target_sql: SQL for the target table.
            source_sql: SQL for the source data.
            on_sql: SQL for the ON condition.
            when_matched: List of dictionaries describing WHEN MATCHED actions.
            when_not_matched: List of dictionaries describing WHEN NOT MATCHED actions.
            all_params: All parameters collected from expressions within the MERGE statement.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted MERGE statement.
        """
        ...  # pragma: no cover


@runtime_checkable
class TemporalTableSupport(Protocol):
    """Protocol for temporal table query support (FOR SYSTEM_TIME)."""

    def supports_temporal_tables(self) -> bool:
        """Whether temporal table queries are supported."""
        ...  # pragma: no cover

    def format_temporal_options(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a temporal table clause (e.g., FOR SYSTEM_TIME AS OF ...).

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover


@runtime_checkable
class QualifyClauseSupport(Protocol):
    """Protocol for QUALIFY clause support."""

    def supports_qualify_clause(self) -> bool:
        """Whether QUALIFY clause is supported."""
        ...  # pragma: no cover

    def format_qualify_clause(
        self,
        qualify_sql: str,
        qualify_params: tuple
    ) -> Tuple[str, tuple]:
        """
        Formats a QUALIFY clause.

        Args:
            qualify_sql: SQL string for the QUALIFY condition.
            qualify_params: Parameters for the QUALIFY condition.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover


@runtime_checkable
class LockingSupport(Protocol):
    """Protocol for row-level locking support (FOR UPDATE, SKIP LOCKED)."""

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        ...  # pragma: no cover

    def format_for_update_clause(
        self,
        options: Dict[str, Any]
    ) -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE/FOR SHARE clause with optional locking modifiers.

        Args:
            options: A dictionary of locking options.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover


