# src/rhosocial/activerecord/backend/dialect/protocols.py
"""
SQL dialect protocol definitions.

This module defines protocol interfaces that dialects can implement to declare
support for advanced database features. Protocols enable fine-grained feature
detection and graceful error handling.
"""
from typing import Any, Dict, List, Optional, Tuple, Protocol, runtime_checkable, TYPE_CHECKING


if TYPE_CHECKING: # pragma: no cover
    from ..expression import (
        bases, ExplainExpression, OnConflictClause, MergeExpression, MatchClause, QualifyClause, GraphEdgeDirection,
        JoinExpression,
        WindowFunctionCall, WindowSpecification, WindowFrameSpecification,
        WindowDefinition, WindowClause
    )
    from ..expression.query_parts import OrderByClause, LimitOffsetClause, ForUpdateClause
    from ..expression.advanced_functions import OrderedSetAggregation
    from ..expression.statements import (
        CreateTableExpression, DropTableExpression, AlterTableExpression,
        CreateViewExpression, DropViewExpression, TruncateExpression,
        CreateSchemaExpression, DropSchemaExpression,
        CreateIndexExpression, DropIndexExpression,
        CreateSequenceExpression, DropSequenceExpression, AlterSequenceExpression,
        CreateMaterializedViewExpression, DropMaterializedViewExpression,
        RefreshMaterializedViewExpression
    )


@runtime_checkable
class WindowFunctionSupport(Protocol):
    """Protocol for window function support."""

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported."""
        ...  # pragma: no cover

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported."""
        ...  # pragma: no cover

    def format_window_function_call(
            self,
            call: "WindowFunctionCall"
    ) -> Tuple[str, tuple]:
        """Format window function call."""
        ...  # pragma: no cover

    def format_window_specification(
            self,
            spec: "WindowSpecification"
    ) -> Tuple[str, tuple]:
        """Format window specification."""
        ...  # pragma: no cover

    def format_window_frame_specification(
            self,
            spec: "WindowFrameSpecification"
    ) -> Tuple[str, tuple]:
        """Format window frame specification."""
        ...  # pragma: no cover

    def format_window_clause(
            self,
            clause: "WindowClause"
    ) -> Tuple[str, tuple]:
        """Format complete WINDOW clause."""
        ...  # pragma: no cover

    def format_window_definition(
            self,
            spec: "WindowDefinition"
    ) -> Tuple[str, tuple]:
        """Format named window definition."""
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

    def format_cte(
        self,
        name: str,
        query_sql: str,
        columns: Optional[List[str]] = None,
        recursive: bool = False,
        materialized: Optional[bool] = None,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        """Format a single CTE definition."""
        ...  # pragma: no cover

    def format_with_query(
        self,
        cte_sql_parts: List[str],
        main_query_sql: str,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> str:
        ...  # pragma: no cover


@runtime_checkable
class WildcardSupport(Protocol):
    """Protocol for wildcard expression support (SELECT *)."""

    def format_wildcard(
        self,
        table: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format wildcard expression (* or table.*)."""
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

    def format_on_conflict_clause(
        self,
        expr: "OnConflictClause"
    ) -> Tuple[str, tuple]:
        """
        Format ON CONFLICT clause.

        Args:
            expr: OnConflictClause object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        ...  # pragma: no cover


@runtime_checkable
class LateralJoinSupport(Protocol):
    """Protocol for LATERAL join support."""

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        ...  # pragma: no cover

    def format_lateral_expression(
        self,
        expr_sql: str,
        expr_params: Tuple[Any, ...],
        alias: Optional[str],
        join_type: str
    ) -> Tuple[str, Tuple]:
        """Format LATERAL expression."""
        ...  # pragma: no cover

    def format_table_function_expression(
        self,
        func_name: str,
        args_sql: List[str],
        args_params: Tuple[Any, ...],
        alias: Optional[str],
        column_names: Optional[List[str]]
    ) -> Tuple[str, Tuple]:
        """Format table-valued function expression."""
        ...  # pragma: no cover


@runtime_checkable
class JoinSupport(Protocol):
    """Protocol for JOIN clause support."""

    def supports_inner_join(self) -> bool:
        """Whether INNER JOIN is supported."""
        ...  # pragma: no cover

    def supports_left_join(self) -> bool:
        """Whether LEFT JOIN and LEFT OUTER JOIN are supported."""
        ...  # pragma: no cover

    def supports_right_join(self) -> bool:
        """Whether RIGHT JOIN and RIGHT OUTER JOIN are supported."""
        ...  # pragma: no cover

    def supports_full_join(self) -> bool:
        """Whether FULL JOIN and FULL OUTER JOIN are supported."""
        ...  # pragma: no cover

    def supports_cross_join(self) -> bool:
        """Whether CROSS JOIN is supported."""
        ...  # pragma: no cover

    def supports_natural_join(self) -> bool:
        """Whether NATURAL JOIN is supported."""
        ...  # pragma: no cover

    def format_join_expression(
        self,
        join_expr: "JoinExpression"
    ) -> Tuple[str, Tuple]:
        """
        Formats a JOIN expression.

        Args:
            join_expr: JoinExpression object.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
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

    def format_array_expression(
        self,
        operation: str,
        elements: Optional[List["bases.BaseExpression"]],
        base_expr: Optional["bases.BaseExpression"],
        index_expr: Optional["bases.BaseExpression"]
    ) -> Tuple[str, Tuple]:
        """Format array expression."""
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

    def format_json_expression(
        self,
        column: Any,
        path: str,
        operation: str
    ) -> Tuple[str, Tuple]:
        """
        Format JSON expression.

        Args:
            column: Column expression or name
            path: JSON path
            operation: JSON operation (e.g., '->', '->>')

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
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

    def format_explain_statement(
        self,
        expr: "ExplainExpression"
    ) -> Tuple[str, tuple]:
        """
        Format EXPLAIN statement.

        Args:
            expr: ExplainExpression object

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted statement.
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
        clause: "MatchClause"
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
        aggregation: "OrderedSetAggregation"
    ) -> Tuple[str, Tuple]:
        """
        Formats an ordered-set aggregate function call.

        Args:
            aggregation: OrderedSetAggregation object to format

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
        expr: "MergeExpression"
    ) -> Tuple[str, tuple]:
        """
        Formats a complete MERGE statement from a MergeExpression object.

        Args:
            expr: MergeExpression object containing the merge specifications

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted statement.
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
        clause: "QualifyClause"
    ) -> Tuple[str, tuple]:
        """
        Formats a QUALIFY clause.

        Args:
            clause: QualifyClause object

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

@runtime_checkable
class SetOperationSupport(Protocol):
    """Protocol for set operation (UNION, INTERSECT, EXCEPT) support."""

    def supports_union(self) -> bool:
        """Whether UNION operation is supported."""
        ...  # pragma: no cover

    def supports_union_all(self) -> bool:
        """Whether UNION ALL operation is supported."""
        ...  # pragma: no cover

    def supports_intersect(self) -> bool:
        """Whether INTERSECT operation is supported."""
        ...  # pragma: no cover

    def supports_except(self) -> bool:
        """Whether EXCEPT operation is supported."""
        ...  # pragma: no cover

    def supports_set_operation_order_by(self) -> bool:
        """Whether set operations support ORDER BY clauses."""
        ...  # pragma: no cover

    def supports_set_operation_limit_offset(self) -> bool:
        """Whether set operations support LIMIT and OFFSET clauses."""
        ...  # pragma: no cover

    def supports_set_operation_for_update(self) -> bool:
        """Whether set operations support FOR UPDATE clauses."""
        ...  # pragma: no cover

    def format_set_operation_expression(
        self,
        left: "bases.BaseExpression",
        right: "bases.BaseExpression",
        operation: str,
        alias: Optional[str],
        all_: bool,
        order_by_clause: Optional["OrderByClause"] = None,
        limit_offset_clause: Optional["LimitOffsetClause"] = None,
        for_update_clause: Optional["ForUpdateClause"] = None
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT)."""
        ... # pragma: no cover


# ============================================================
# DDL (Data Definition Language) Support Protocols
# ============================================================

@runtime_checkable
class TableSupport(Protocol):
    """
    Protocol for table DDL support.
    
    This protocol covers CREATE TABLE, DROP TABLE, and ALTER TABLE operations.
    Most SQL databases support these operations, but feature support varies:
    - IF NOT EXISTS / IF EXISTS clauses
    - TEMPORARY tables
    - Table inheritance (PostgreSQL)
    - Partitioning
    - Storage options
    """
    
    def supports_create_table(self) -> bool:
        """Whether CREATE TABLE is supported."""
        ... # pragma: no cover
    
    def supports_drop_table(self) -> bool:
        """Whether DROP TABLE is supported."""
        ... # pragma: no cover
    
    def supports_alter_table(self) -> bool:
        """Whether ALTER TABLE is supported."""
        ... # pragma: no cover
    
    def supports_temporary_table(self) -> bool:
        """Whether TEMPORARY tables are supported."""
        ... # pragma: no cover
    
    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_table_inheritance(self) -> bool:
        """Whether table inheritance (PostgreSQL INHERITS) is supported."""
        ... # pragma: no cover
    
    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported."""
        ... # pragma: no cover
    
    def supports_table_tablespace(self) -> bool:
        """Whether tablespace specification is supported."""
        ... # pragma: no cover
    
    def supports_drop_column(self) -> bool:
        """Whether DROP COLUMN is supported in ALTER TABLE."""
        ... # pragma: no cover
    
    def supports_alter_column_type(self) -> bool:
        """Whether altering column data type is supported."""
        ... # pragma: no cover
    
    def supports_rename_column(self) -> bool:
        """Whether RENAME COLUMN is supported."""
        ... # pragma: no cover
    
    def supports_rename_table(self) -> bool:
        """Whether RENAME TABLE is supported."""
        ... # pragma: no cover
    
    def supports_add_constraint(self) -> bool:
        """Whether ADD CONSTRAINT is supported."""
        ... # pragma: no cover
    
    def supports_drop_constraint(self) -> bool:
        """Whether DROP CONSTRAINT is supported."""
        ... # pragma: no cover
    
    def format_create_table_statement(
        self,
        expr: "CreateTableExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE TABLE statement."""
        ... # pragma: no cover
    
    def format_drop_table_statement(
        self,
        expr: "DropTableExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP TABLE statement."""
        ... # pragma: no cover
    
    def format_alter_table_statement(
        self,
        expr: "AlterTableExpression"
    ) -> Tuple[str, tuple]:
        """Format ALTER TABLE statement."""
        ... # pragma: no cover


@runtime_checkable
class ViewSupport(Protocol):
    """
    Protocol for view DDL support.

    This protocol covers CREATE VIEW and DROP VIEW operations.
    Feature support varies across databases:
    - CREATE OR REPLACE VIEW
    - TEMPORARY views
    - Materialized views (PostgreSQL)
    - WITH CHECK OPTION
    - Algorithm options (MySQL)
    """

    def supports_create_view(self) -> bool:
        """Whether CREATE VIEW is supported."""
        ... # pragma: no cover

    def supports_drop_view(self) -> bool:
        """Whether DROP VIEW is supported."""
        ... # pragma: no cover

    def supports_or_replace_view(self) -> bool:
        """Whether CREATE OR REPLACE VIEW is supported."""
        ... # pragma: no cover

    def supports_temporary_view(self) -> bool:
        """Whether TEMPORARY views are supported."""
        ... # pragma: no cover

    def supports_materialized_view(self) -> bool:
        """Whether materialized views are supported."""
        ... # pragma: no cover

    def supports_refresh_materialized_view(self) -> bool:
        """Whether REFRESH MATERIALIZED VIEW is supported."""
        ... # pragma: no cover

    def supports_materialized_view_concurrent_refresh(self) -> bool:
        """Whether concurrent refresh for materialized views is supported."""
        ... # pragma: no cover

    def supports_materialized_view_tablespace(self) -> bool:
        """Whether tablespace specification for materialized views is supported."""
        ... # pragma: no cover

    def supports_materialized_view_storage_options(self) -> bool:
        """Whether storage options for materialized views are supported."""
        ... # pragma: no cover

    def supports_if_exists_view(self) -> bool:
        """Whether DROP VIEW IF EXISTS is supported."""
        ... # pragma: no cover

    def supports_view_check_option(self) -> bool:
        """Whether WITH CHECK OPTION is supported."""
        ... # pragma: no cover

    def supports_cascade_view(self) -> bool:
        """Whether DROP VIEW CASCADE is supported."""
        ... # pragma: no cover

    def format_create_view_statement(
        self,
        expr: "CreateViewExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE VIEW statement."""
        ... # pragma: no cover

    def format_drop_view_statement(
        self,
        expr: "DropViewExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP VIEW statement."""
        ... # pragma: no cover

    def format_create_materialized_view_statement(
        self,
        expr: "CreateMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE MATERIALIZED VIEW statement."""
        ... # pragma: no cover

    def format_drop_materialized_view_statement(
        self,
        expr: "DropMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP MATERIALIZED VIEW statement."""
        ... # pragma: no cover

    def format_refresh_materialized_view_statement(
        self,
        expr: "RefreshMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format REFRESH MATERIALIZED VIEW statement."""
        ... # pragma: no cover


@runtime_checkable
class TruncateSupport(Protocol):
    """
    Protocol for TRUNCATE TABLE support.
    
    TRUNCATE provides a fast way to delete all rows from a table.
    Feature support varies:
    - TRUNCATE TABLE keyword requirement
    - RESTART IDENTITY (PostgreSQL)
    - CASCADE option (PostgreSQL)
    """
    
    def supports_truncate(self) -> bool:
        """Whether TRUNCATE is supported."""
        ... # pragma: no cover
    
    def supports_truncate_table_keyword(self) -> bool:
        """Whether TABLE keyword is required or optional in TRUNCATE."""
        ... # pragma: no cover
    
    def supports_truncate_restart_identity(self) -> bool:
        """Whether RESTART IDENTITY is supported."""
        ... # pragma: no cover
    
    def supports_truncate_cascade(self) -> bool:
        """Whether CASCADE option is supported."""
        ... # pragma: no cover
    
    def format_truncate_statement(
        self,
        expr: "TruncateExpression"
    ) -> Tuple[str, tuple]:
        """Format TRUNCATE TABLE statement."""
        ... # pragma: no cover


@runtime_checkable
class SchemaSupport(Protocol):
    """
    Protocol for schema (namespace) DDL support.
    
    Schemas are database namespaces that contain tables, views, and other objects.
    Support varies significantly:
    - PostgreSQL: Native schema support
    - MySQL: CREATE SCHEMA is synonym for CREATE DATABASE
    - SQLite: No schema concept (database file is the entire database)
    """
    
    def supports_create_schema(self) -> bool:
        """Whether CREATE SCHEMA is supported."""
        ... # pragma: no cover
    
    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is supported."""
        ... # pragma: no cover
    
    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_schema_cascade(self) -> bool:
        """Whether DROP SCHEMA CASCADE is supported."""
        ... # pragma: no cover
    
    def supports_schema_authorization(self) -> bool:
        """Whether AUTHORIZATION clause is supported."""
        ... # pragma: no cover
    
    def format_create_schema_statement(
        self,
        expr: "CreateSchemaExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE SCHEMA statement."""
        ... # pragma: no cover
    
    def format_drop_schema_statement(
        self,
        expr: "DropSchemaExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP SCHEMA statement."""
        ... # pragma: no cover


@runtime_checkable
class IndexSupport(Protocol):
    """
    Protocol for index DDL support.
    
    Note: This protocol is for standalone CREATE INDEX / DROP INDEX statements.
    Inline index definitions in CREATE TABLE are handled separately.
    
    Feature support varies:
    - PostgreSQL: BTREE, HASH, GIN, GIST, SPGIST, BRIN; partial indexes; INCLUDE
    - MySQL: BTREE, HASH; USING clause; no partial indexes
    - SQLite: Partial indexes (WHERE); functional indexes; always B-tree
    """
    
    def supports_create_index(self) -> bool:
        """Whether CREATE INDEX is supported."""
        ... # pragma: no cover
    
    def supports_drop_index(self) -> bool:
        """Whether DROP INDEX is supported."""
        ... # pragma: no cover
    
    def supports_unique_index(self) -> bool:
        """Whether UNIQUE indexes are supported."""
        ... # pragma: no cover
    
    def supports_index_if_not_exists(self) -> bool:
        """Whether CREATE INDEX IF NOT EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_index_if_exists(self) -> bool:
        """Whether DROP INDEX IF EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_index_type(self) -> bool:
        """Whether index type specification (USING BTREE/HASH) is supported."""
        ... # pragma: no cover
    
    def supports_partial_index(self) -> bool:
        """Whether partial indexes (WHERE clause) are supported."""
        ... # pragma: no cover
    
    def supports_functional_index(self) -> bool:
        """Whether functional/expression indexes are supported."""
        ... # pragma: no cover
    
    def supports_index_include(self) -> bool:
        """Whether INCLUDE clause (covering columns) is supported."""
        ... # pragma: no cover
    
    def supports_index_tablespace(self) -> bool:
        """Whether tablespace specification for indexes is supported."""
        ... # pragma: no cover
    
    def supports_concurrent_index(self) -> bool:
        """Whether CREATE INDEX CONCURRENTLY (PostgreSQL) is supported."""
        ... # pragma: no cover
    
    def get_supported_index_types(self) -> List[str]:
        """Return list of supported index types (e.g., ['BTREE', 'HASH'])."""
        ... # pragma: no cover
    
    def format_create_index_statement(
        self,
        expr: "CreateIndexExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE INDEX statement."""
        ... # pragma: no cover
    
    def format_drop_index_statement(
        self,
        expr: "DropIndexExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP INDEX statement."""
        ... # pragma: no cover


@runtime_checkable
class SequenceSupport(Protocol):
    """
    Protocol for sequence object DDL support.
    
    Sequences are used for generating unique numbers, typically for auto-increment.
    Support varies:
    - PostgreSQL: Native SEQUENCE objects with full options
    - MySQL: No sequence objects (uses AUTO_INCREMENT)
    - SQLite: No sequences (uses AUTOINCREMENT keyword)
    - Oracle: SEQUENCE objects with many options
    """
    
    def supports_sequence(self) -> bool:
        """Whether sequence objects are supported."""
        ... # pragma: no cover
    
    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported."""
        ... # pragma: no cover
    
    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported."""
        ... # pragma: no cover
    
    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported."""
        ... # pragma: no cover
    
    def supports_sequence_if_not_exists(self) -> bool:
        """Whether CREATE SEQUENCE IF NOT EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_sequence_if_exists(self) -> bool:
        """Whether DROP SEQUENCE IF EXISTS is supported."""
        ... # pragma: no cover
    
    def supports_sequence_cycle(self) -> bool:
        """Whether CYCLE/NO CYCLE option is supported."""
        ... # pragma: no cover
    
    def supports_sequence_cache(self) -> bool:
        """Whether CACHE option is supported."""
        ... # pragma: no cover
    
    def supports_sequence_order(self) -> bool:
        """Whether ORDER option is supported."""
        ... # pragma: no cover
    
    def supports_sequence_owned_by(self) -> bool:
        """Whether OWNED BY clause is supported."""
        ... # pragma: no cover
    
    def format_create_sequence_statement(
        self,
        expr: "CreateSequenceExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement."""
        ... # pragma: no cover
    
    def format_drop_sequence_statement(
        self,
        expr: "DropSequenceExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement."""
        ... # pragma: no cover
    
    def format_alter_sequence_statement(
        self,
        expr: "AlterSequenceExpression"
    ) -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement."""
        ... # pragma: no cover

