# src/rhosocial/activerecord/backend/dialect/protocols.py
"""
SQL dialect protocol definitions.

This module defines protocol interfaces that dialects can implement to declare
support for advanced database features. Protocols enable fine-grained feature
detection and graceful error handling.
"""

from typing import Any, Dict, List, Optional, Tuple, Protocol, runtime_checkable, TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no cover
    from ..expression import (
        bases,
        ExplainExpression,
        OnConflictClause,
        MergeExpression,
        MatchClause,
        QualifyClause,
        GraphEdgeDirection,
        JoinExpression,
        WindowFunctionCall,
        WindowSpecification,
        WindowFrameSpecification,
        WindowDefinition,
        WindowClause,
        # Transaction expressions
        BeginTransactionExpression,
        CommitTransactionExpression,
        RollbackTransactionExpression,
        SavepointExpression,
        ReleaseSavepointExpression,
        SetTransactionExpression,
    )
    from ..expression.query_parts import OrderByClause, LimitOffsetClause, ForUpdateClause
    from ..expression.advanced_functions import OrderedSetAggregation
    from ..expression.statements import (
        CreateTableExpression,
        DropTableExpression,
        AlterTableExpression,
        CreateViewExpression,
        DropViewExpression,
        TruncateExpression,
        CreateSchemaExpression,
        DropSchemaExpression,
        CreateIndexExpression,
        DropIndexExpression,
        CreateSequenceExpression,
        DropSequenceExpression,
        AlterSequenceExpression,
        CreateMaterializedViewExpression,
        DropMaterializedViewExpression,
        RefreshMaterializedViewExpression,
        CreateTriggerExpression,
        DropTriggerExpression,
        CreateFunctionExpression,
        DropFunctionExpression,
        CreateFulltextIndexExpression,
        DropFulltextIndexExpression,
        ReturningClause,
    )
    from ..introspection.expressions import (
        DatabaseInfoExpression,
        TableListExpression,
        TableInfoExpression,
        ColumnInfoExpression,
        IndexInfoExpression,
        ForeignKeyExpression,
        ViewListExpression,
        ViewInfoExpression,
        TriggerListExpression,
        TriggerInfoExpression,
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

    def format_window_function_call(self, call: "WindowFunctionCall") -> Tuple[str, tuple]:
        """Format window function call."""
        ...  # pragma: no cover

    def format_window_specification(self, spec: "WindowSpecification") -> Tuple[str, tuple]:
        """Format window specification."""
        ...  # pragma: no cover

    def format_window_frame_specification(self, spec: "WindowFrameSpecification") -> Tuple[str, tuple]:
        """Format window frame specification."""
        ...  # pragma: no cover

    def format_window_clause(self, clause: "WindowClause") -> Tuple[str, tuple]:
        """Format complete WINDOW clause."""
        ...  # pragma: no cover

    def format_window_definition(self, spec: "WindowDefinition") -> Tuple[str, tuple]:
        """Format named window definition."""
        ...  # pragma: no cover


@runtime_checkable
class TriggerSupport(Protocol):
    """Protocol for trigger DDL support (SQL:1999/PSM)."""

    def supports_trigger(self) -> bool:
        """Whether triggers are supported."""
        ...  # pragma: no cover

    def supports_create_trigger(self) -> bool:
        """Whether CREATE TRIGGER is supported."""
        ...  # pragma: no cover

    def supports_drop_trigger(self) -> bool:
        """Whether DROP TRIGGER is supported."""
        ...  # pragma: no cover

    def supports_instead_of_trigger(self) -> bool:
        """Whether INSTEAD OF triggers are supported (for views)."""
        ...  # pragma: no cover

    def supports_statement_trigger(self) -> bool:
        """Whether FOR EACH STATEMENT triggers are supported."""
        ...  # pragma: no cover

    def supports_trigger_referencing(self) -> bool:
        """Whether REFERENCING clause is supported."""
        ...  # pragma: no cover

    def supports_trigger_when(self) -> bool:
        """Whether WHEN condition is supported."""
        ...  # pragma: no cover

    def supports_trigger_if_not_exists(self) -> bool:
        """Whether CREATE TRIGGER IF NOT EXISTS is supported."""
        ...  # pragma: no cover

    def format_create_trigger_statement(self, expr: "CreateTriggerExpression") -> Tuple[str, tuple]:
        """Format CREATE TRIGGER statement."""
        ...  # pragma: no cover

    def format_drop_trigger_statement(self, expr: "DropTriggerExpression") -> Tuple[str, tuple]:
        """Format DROP TRIGGER statement."""
        ...  # pragma: no cover


@runtime_checkable
class FunctionSupport(Protocol):
    """Protocol for function DDL support (SQL/PSM)."""

    def supports_function(self) -> bool:
        """Whether functions are supported."""
        ...  # pragma: no cover

    def supports_create_function(self) -> bool:
        """Whether CREATE FUNCTION is supported."""
        ...  # pragma: no cover

    def supports_drop_function(self) -> bool:
        """Whether DROP FUNCTION is supported."""
        ...  # pragma: no cover

    def supports_function_or_replace(self) -> bool:
        """Whether CREATE OR REPLACE FUNCTION is supported."""
        ...  # pragma: no cover

    def supports_function_parameters(self) -> bool:
        """Whether function parameters are supported."""
        ...  # pragma: no cover

    def format_create_function_statement(self, expr: "CreateFunctionExpression") -> Tuple[str, tuple]:
        """Format CREATE FUNCTION statement."""
        ...  # pragma: no cover

    def format_drop_function_statement(self, expr: "DropFunctionExpression") -> Tuple[str, tuple]:
        """Format DROP FUNCTION statement."""
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
        dialect_options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Format a single CTE definition."""
        ...  # pragma: no cover

    def format_with_query(
        self, cte_sql_parts: List[str], main_query_sql: str, dialect_options: Optional[Dict[str, Any]] = None
    ) -> str: ...  # pragma: no cover


@runtime_checkable
class WildcardSupport(Protocol):
    """Protocol for wildcard expression support (SELECT *)."""

    def format_wildcard(self, table: Optional[str] = None) -> Tuple[str, Tuple]:
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
        self, operation: str, expressions: List["bases.BaseExpression"]
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

    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, Tuple]:
        """
        Format a RETURNING clause.

        Args:
            clause: ReturningClause object containing expressions to return

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

    def format_on_conflict_clause(self, expr: "OnConflictClause") -> Tuple[str, tuple]:
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
        self, expr_sql: str, expr_params: Tuple[Any, ...], alias: Optional[str], join_type: str
    ) -> Tuple[str, Tuple]:
        """Format LATERAL expression."""
        ...  # pragma: no cover

    def format_table_function_expression(
        self,
        func_name: str,
        args_sql: List[str],
        args_params: Tuple[Any, ...],
        alias: Optional[str],
        column_names: Optional[List[str]],
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

    def format_join_expression(self, join_expr: "JoinExpression") -> Tuple[str, Tuple]:
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
        index_expr: Optional["bases.BaseExpression"],
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

    def format_json_expression(self, column: Any, path: str, operation: str) -> Tuple[str, Tuple]:
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
        self, json_col_sql: str, path: str, columns: List[Dict[str, Any]], alias: Optional[str], params: tuple
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

    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
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

    def format_graph_vertex(self, variable: str, table: str) -> Tuple[str, tuple]:
        """
        Formats a graph vertex expression.

        Args:
            variable: The vertex variable name.
            table: The vertex table name.

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover

    def format_graph_edge(self, variable: str, table: str, direction: "GraphEdgeDirection") -> Tuple[str, tuple]:
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

    def format_match_clause(self, clause: "MatchClause") -> Tuple[str, tuple]:
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

    def format_filter_clause(self, condition_sql: str, condition_params: tuple) -> Tuple[str, Tuple]:
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

    def format_ordered_set_aggregation(self, aggregation: "OrderedSetAggregation") -> Tuple[str, Tuple]:
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

    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
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

    def format_temporal_options(self, options: Dict[str, Any]) -> Tuple[str, tuple]:
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

    def format_qualify_clause(self, clause: "QualifyClause") -> Tuple[str, tuple]:
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

    def format_for_update_clause(self, clause: "ForUpdateClause") -> Tuple[str, tuple]:
        """
        Formats a FOR UPDATE clause with optional locking modifiers.

        Args:
            clause: ForUpdateClause object containing locking options

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
        for_update_clause: Optional["ForUpdateClause"] = None,
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT)."""
        ...  # pragma: no cover


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
        ...  # pragma: no cover

    def supports_drop_table(self) -> bool:
        """Whether DROP TABLE is supported."""
        ...  # pragma: no cover

    def supports_alter_table(self) -> bool:
        """Whether ALTER TABLE is supported."""
        ...  # pragma: no cover

    def supports_temporary_table(self) -> bool:
        """Whether TEMPORARY tables are supported."""
        ...  # pragma: no cover

    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        ...  # pragma: no cover

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        ...  # pragma: no cover

    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported."""
        ...  # pragma: no cover

    def supports_table_tablespace(self) -> bool:
        """Whether tablespace specification is supported."""
        ...  # pragma: no cover

    def supports_drop_column(self) -> bool:
        """Whether DROP COLUMN is supported in ALTER TABLE."""
        ...  # pragma: no cover

    def supports_alter_column_type(self) -> bool:
        """Whether altering column data type is supported."""
        ...  # pragma: no cover

    def supports_rename_column(self) -> bool:
        """Whether RENAME COLUMN is supported."""
        ...  # pragma: no cover

    def supports_rename_table(self) -> bool:
        """Whether RENAME TABLE is supported."""
        ...  # pragma: no cover

    def supports_add_constraint(self) -> bool:
        """Whether ADD CONSTRAINT is supported."""
        ...  # pragma: no cover

    def supports_drop_constraint(self) -> bool:
        """Whether DROP CONSTRAINT is supported."""
        ...  # pragma: no cover

    def format_create_table_statement(self, expr: "CreateTableExpression") -> Tuple[str, tuple]:
        """Format CREATE TABLE statement."""
        ...  # pragma: no cover

    def format_drop_table_statement(self, expr: "DropTableExpression") -> Tuple[str, tuple]:
        """Format DROP TABLE statement."""
        ...  # pragma: no cover

    def format_alter_table_statement(self, expr: "AlterTableExpression") -> Tuple[str, tuple]:
        """Format ALTER TABLE statement."""
        ...  # pragma: no cover


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
        ...  # pragma: no cover

    def supports_drop_view(self) -> bool:
        """Whether DROP VIEW is supported."""
        ...  # pragma: no cover

    def supports_or_replace_view(self) -> bool:
        """Whether CREATE OR REPLACE VIEW is supported."""
        ...  # pragma: no cover

    def supports_temporary_view(self) -> bool:
        """Whether TEMPORARY views are supported."""
        ...  # pragma: no cover

    def supports_materialized_view(self) -> bool:
        """Whether materialized views are supported."""
        ...  # pragma: no cover

    def supports_refresh_materialized_view(self) -> bool:
        """Whether REFRESH MATERIALIZED VIEW is supported."""
        ...  # pragma: no cover

    def supports_materialized_view_tablespace(self) -> bool:
        """Whether tablespace specification for materialized views is supported."""
        ...  # pragma: no cover

    def supports_materialized_view_storage_options(self) -> bool:
        """Whether storage options for materialized views are supported."""
        ...  # pragma: no cover

    def supports_if_exists_view(self) -> bool:
        """Whether DROP VIEW IF EXISTS is supported."""
        ...  # pragma: no cover

    def supports_view_check_option(self) -> bool:
        """Whether WITH CHECK OPTION is supported."""
        ...  # pragma: no cover

    def supports_cascade_view(self) -> bool:
        """Whether DROP VIEW CASCADE is supported."""
        ...  # pragma: no cover

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
        """Format CREATE VIEW statement."""
        ...  # pragma: no cover

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement."""
        ...  # pragma: no cover

    def format_create_materialized_view_statement(self, expr: "CreateMaterializedViewExpression") -> Tuple[str, tuple]:
        """Format CREATE MATERIALIZED VIEW statement."""
        ...  # pragma: no cover

    def format_drop_materialized_view_statement(self, expr: "DropMaterializedViewExpression") -> Tuple[str, tuple]:
        """Format DROP MATERIALIZED VIEW statement."""
        ...  # pragma: no cover

    def format_refresh_materialized_view_statement(
        self, expr: "RefreshMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format REFRESH MATERIALIZED VIEW statement."""
        ...  # pragma: no cover


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
        ...  # pragma: no cover

    def supports_truncate_table_keyword(self) -> bool:
        """Whether TABLE keyword is required or optional in TRUNCATE."""
        ...  # pragma: no cover

    def supports_truncate_restart_identity(self) -> bool:
        """Whether RESTART IDENTITY is supported."""
        ...  # pragma: no cover

    def supports_truncate_cascade(self) -> bool:
        """Whether CASCADE option is supported."""
        ...  # pragma: no cover

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format TRUNCATE TABLE statement."""
        ...  # pragma: no cover


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
        ...  # pragma: no cover

    def supports_drop_schema(self) -> bool:
        """Whether DROP SCHEMA is supported."""
        ...  # pragma: no cover

    def supports_schema_if_not_exists(self) -> bool:
        """Whether CREATE SCHEMA IF NOT EXISTS is supported."""
        ...  # pragma: no cover

    def supports_schema_if_exists(self) -> bool:
        """Whether DROP SCHEMA IF EXISTS is supported."""
        ...  # pragma: no cover

    def supports_schema_cascade(self) -> bool:
        """Whether DROP SCHEMA CASCADE is supported."""
        ...  # pragma: no cover

    def supports_schema_authorization(self) -> bool:
        """Whether AUTHORIZATION clause is supported."""
        ...  # pragma: no cover

    def format_create_schema_statement(self, expr: "CreateSchemaExpression") -> Tuple[str, tuple]:
        """Format CREATE SCHEMA statement."""
        ...  # pragma: no cover

    def format_drop_schema_statement(self, expr: "DropSchemaExpression") -> Tuple[str, tuple]:
        """Format DROP SCHEMA statement."""
        ...  # pragma: no cover


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
        ...  # pragma: no cover

    def supports_drop_index(self) -> bool:
        """Whether DROP INDEX is supported."""
        ...  # pragma: no cover

    def supports_unique_index(self) -> bool:
        """Whether UNIQUE indexes are supported."""
        ...  # pragma: no cover

    def supports_index_if_not_exists(self) -> bool:
        """Whether CREATE INDEX IF NOT EXISTS is supported."""
        ...  # pragma: no cover

    def supports_index_if_exists(self) -> bool:
        """Whether DROP INDEX IF EXISTS is supported."""
        ...  # pragma: no cover

    def supports_index_type(self) -> bool:
        """Whether index type specification (USING BTREE/HASH) is supported."""
        ...  # pragma: no cover

    def supports_partial_index(self) -> bool:
        """Whether partial indexes (WHERE clause) are supported."""
        ...  # pragma: no cover

    def supports_functional_index(self) -> bool:
        """Whether functional/expression indexes are supported."""
        ...  # pragma: no cover

    def supports_index_include(self) -> bool:
        """Whether INCLUDE clause (covering columns) is supported."""
        ...  # pragma: no cover

    def supports_index_tablespace(self) -> bool:
        """Whether tablespace specification for indexes is supported."""
        ...  # pragma: no cover

    def supports_concurrent_index(self) -> bool:
        """Whether CREATE INDEX CONCURRENTLY (PostgreSQL) is supported."""
        ...  # pragma: no cover

    def get_supported_index_types(self) -> List[str]:
        """Return list of supported index types (e.g., ['BTREE', 'HASH'])."""
        ...  # pragma: no cover

    def supports_fulltext_index(self) -> bool:
        """Whether FULLTEXT indexes are supported."""
        ...  # pragma: no cover

    def supports_fulltext_parser(self) -> bool:
        """Whether FULLTEXT parser plugin is supported."""
        ...  # pragma: no cover

    def supports_fulltext_boolean_mode(self) -> bool:
        """Whether BOOLEAN MODE in MATCH is supported."""
        ...  # pragma: no cover

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether QUERY EXPANSION in MATCH is supported."""
        ...  # pragma: no cover

    def format_fulltext_match(
        self, columns: List[str], search_term: str, mode: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format MATCH ... AGAINST expression for full-text search.

        Args:
            columns: Columns to search
            search_term: Search term or query
            mode: Search mode ('NATURAL LANGUAGE', 'BOOLEAN', 'QUERY EXPANSION')

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

    def format_create_fulltext_index_statement(self, expr: "CreateFulltextIndexExpression") -> Tuple[str, tuple]:
        """Format CREATE FULLTEXT INDEX statement.

        Args:
            expr: CreateFulltextIndexExpression object

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

    def format_drop_fulltext_index_statement(self, expr: "DropFulltextIndexExpression") -> Tuple[str, tuple]:
        """Format DROP FULLTEXT INDEX statement.

        Args:
            expr: DropFulltextIndexExpression object

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        ...  # pragma: no cover

    def format_create_index_statement(self, expr: "CreateIndexExpression") -> Tuple[str, tuple]:
        """Format CREATE INDEX statement."""
        ...  # pragma: no cover

    def format_drop_index_statement(self, expr: "DropIndexExpression") -> Tuple[str, tuple]:
        """Format DROP INDEX statement."""
        ...  # pragma: no cover


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
        ...  # pragma: no cover

    def supports_create_sequence(self) -> bool:
        """Whether CREATE SEQUENCE is supported."""
        ...  # pragma: no cover

    def supports_drop_sequence(self) -> bool:
        """Whether DROP SEQUENCE is supported."""
        ...  # pragma: no cover

    def supports_alter_sequence(self) -> bool:
        """Whether ALTER SEQUENCE is supported."""
        ...  # pragma: no cover

    def supports_sequence_if_not_exists(self) -> bool:
        """Whether CREATE SEQUENCE IF NOT EXISTS is supported."""
        ...  # pragma: no cover

    def supports_sequence_if_exists(self) -> bool:
        """Whether DROP SEQUENCE IF EXISTS is supported."""
        ...  # pragma: no cover

    def supports_sequence_cycle(self) -> bool:
        """Whether CYCLE/NO CYCLE option is supported."""
        ...  # pragma: no cover

    def supports_sequence_cache(self) -> bool:
        """Whether CACHE option is supported."""
        ...  # pragma: no cover

    def supports_sequence_order(self) -> bool:
        """Whether ORDER option is supported."""
        ...  # pragma: no cover

    def supports_sequence_owned_by(self) -> bool:
        """Whether OWNED BY clause is supported."""
        ...  # pragma: no cover

    def format_create_sequence_statement(self, expr: "CreateSequenceExpression") -> Tuple[str, tuple]:
        """Format CREATE SEQUENCE statement."""
        ...  # pragma: no cover

    def format_drop_sequence_statement(self, expr: "DropSequenceExpression") -> Tuple[str, tuple]:
        """Format DROP SEQUENCE statement."""
        ...  # pragma: no cover

    def format_alter_sequence_statement(self, expr: "AlterSequenceExpression") -> Tuple[str, tuple]:
        """Format ALTER SEQUENCE statement."""
        ...  # pragma: no cover


@runtime_checkable
class ILIKESupport(Protocol):
    """
    Protocol for ILIKE (case-insensitive LIKE) support.

    ILIKE is a PostgreSQL extension for case-insensitive pattern matching.
    Support varies across databases:
    - PostgreSQL: Native ILIKE operator
    - MySQL: Uses LIKE with case-insensitive collation or LOWER() function
    - SQLite: No native ILIKE (requires LOWER() workaround)
    - Oracle: Uses UPPER() or LOWER() with LIKE
    """

    def supports_ilike(self) -> bool:
        """Whether ILIKE operator is supported."""
        ...  # pragma: no cover

    def format_ilike_expression(self, column: Any, pattern: str, negate: bool = False) -> Tuple[str, Tuple]:
        """
        Format ILIKE expression (case-insensitive pattern matching).

        Args:
            column: Column expression or name
            pattern: Pattern to match (with % and _ wildcards)
            negate: If True, format NOT ILIKE expression

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        ...  # pragma: no cover


@runtime_checkable
class GeneratedColumnSupport(Protocol):
    """
    Protocol for generated column (computed column) support.

    Generated columns are columns whose value is computed from an expression
    rather than being stored directly. Support varies:
    - SQLite: STORED and VIRTUAL since 3.31.0
    - PostgreSQL: STORED only (via GENERATED ALWAYS AS)
    - MySQL: STORED and VIRTUAL since 5.7
    """

    def supports_generated_columns(self) -> bool:
        """Whether generated columns are supported."""
        ...  # pragma: no cover

    def supports_stored_generated_columns(self) -> bool:
        """Whether STORED generated columns are supported."""
        ...  # pragma: no cover

    def supports_virtual_generated_columns(self) -> bool:
        """Whether VIRTUAL generated columns are supported."""
        ...  # pragma: no cover


# ============================================================
# Introspection Support Protocol
# ============================================================


if TYPE_CHECKING:  # pragma: no cover
    from ..introspection.types import (
        IntrospectionScope,
    )


@runtime_checkable
class IntrospectionSupport(Protocol):
    """
    Protocol for database introspection capability declaration.

    This protocol defines methods that dialects implement to declare which
    introspection features they support. Dialects also provide format_*
    methods to generate database-specific SQL for introspection queries.

    Layer responsibilities:
    - Dialect layer: Declares capabilities (supports_*) and formats SQL (format_*)
    - Backend layer: Executes queries and parses results

    Expression pattern:
    - Expressions collect parameters (table_name, schema, options, etc.)
    - Dialects generate SQL from expression parameters
    - Backends execute SQL and parse results
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported."""
        ...  # pragma: no cover

    def supports_database_info(self) -> bool:
        """Whether database information query is supported."""
        ...  # pragma: no cover

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported."""
        ...  # pragma: no cover

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported."""
        ...  # pragma: no cover

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported."""
        ...  # pragma: no cover

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported."""
        ...  # pragma: no cover

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported."""
        ...  # pragma: no cover

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported."""
        ...  # pragma: no cover

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported."""
        ...  # pragma: no cover

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """Whether partition information introspection is supported."""
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported."""
        ...  # pragma: no cover

    def supports_extensions(self) -> bool:
        """Whether installed extensions introspection is supported."""
        ...  # pragma: no cover

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported."""
        ...  # pragma: no cover

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required)."""
        ...  # pragma: no cover

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        ...  # pragma: no cover

    # ========== Query Formatting ==========

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover


@runtime_checkable
class AsyncIntrospectionSupport(Protocol):
    """
    Protocol for async database introspection capability declaration.

    This protocol defines methods that dialects implement to declare which
    introspection features they support. Dialects also provide format_*
    methods to generate database-specific SQL for introspection queries.

    Layer responsibilities:
    - Dialect layer: Declares capabilities (supports_*) and formats SQL (format_*)
    - Backend layer: Executes queries and parses results

    Expression pattern:
    - Expressions collect parameters (table_name, schema, options, etc.)
    - Dialects generate SQL from expression parameters
    - Backends execute SQL and parse results

    Note: The format_* methods are synchronous even in async context because
    they only generate SQL strings without database I/O.
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """Whether introspection is supported."""
        ...  # pragma: no cover

    def supports_database_info(self) -> bool:
        """Whether database information query is supported."""
        ...  # pragma: no cover

    def supports_table_introspection(self) -> bool:
        """Whether table introspection is supported."""
        ...  # pragma: no cover

    def supports_column_introspection(self) -> bool:
        """Whether column introspection is supported."""
        ...  # pragma: no cover

    def supports_index_introspection(self) -> bool:
        """Whether index introspection is supported."""
        ...  # pragma: no cover

    def supports_foreign_key_introspection(self) -> bool:
        """Whether foreign key introspection is supported."""
        ...  # pragma: no cover

    def supports_view_introspection(self) -> bool:
        """Whether view introspection is supported."""
        ...  # pragma: no cover

    def supports_trigger_introspection(self) -> bool:
        """Whether trigger introspection is supported."""
        ...  # pragma: no cover

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """Whether runtime statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_table_stats(self) -> bool:
        """Whether table statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_index_stats(self) -> bool:
        """Whether index statistics introspection is supported."""
        ...  # pragma: no cover

    def supports_unused_indexes_detection(self) -> bool:
        """Whether unused indexes detection is supported."""
        ...  # pragma: no cover

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """Whether partition information introspection is supported."""
        ...  # pragma: no cover

    def supports_object_dependencies(self) -> bool:
        """Whether object dependencies introspection is supported."""
        ...  # pragma: no cover

    def supports_extensions(self) -> bool:
        """Whether installed extensions introspection is supported."""
        ...  # pragma: no cover

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether DDL extraction is supported."""
        ...  # pragma: no cover

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required)."""
        ...  # pragma: no cover

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        ...  # pragma: no cover

    # ========== Query Formatting ==========

    def format_database_info_query(self, expr: "DatabaseInfoExpression") -> Tuple[str, tuple]:
        """
        Format database information query.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_list_query(self, expr: "TableListExpression") -> Tuple[str, tuple]:
        """
        Format table list query.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_table_info_query(self, expr: "TableInfoExpression") -> Tuple[str, tuple]:
        """
        Format single table information query.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_column_info_query(self, expr: "ColumnInfoExpression") -> Tuple[str, tuple]:
        """
        Format column information query.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_index_info_query(self, expr: "IndexInfoExpression") -> Tuple[str, tuple]:
        """
        Format index information query.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_foreign_key_query(self, expr: "ForeignKeyExpression") -> Tuple[str, tuple]:
        """
        Format foreign key information query.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_list_query(self, expr: "ViewListExpression") -> Tuple[str, tuple]:
        """
        Format view list query.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_view_info_query(self, expr: "ViewInfoExpression") -> Tuple[str, tuple]:
        """
        Format single view information query.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_list_query(self, expr: "TriggerListExpression") -> Tuple[str, tuple]:
        """
        Format trigger list query.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_trigger_info_query(self, expr: "TriggerInfoExpression") -> Tuple[str, tuple]:
        """
        Format single trigger information query.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover


@runtime_checkable
class TransactionControlSupport(Protocol):
    """
    Protocol for transaction control statement support.

    This protocol defines methods that dialects implement to declare which
    transaction control features they support. Dialects also provide format_*
    methods to generate database-specific SQL for transaction control statements.

    Layer responsibilities:
    - Dialect layer: Declares capabilities (supports_*) and formats SQL (format_*)
    - Backend layer: Executes SQL and manages transaction state

    Expression pattern:
    - Expressions collect parameters (isolation_level, mode, etc.)
    - Dialects generate SQL from expression parameters
    - Backends execute SQL and manage state

    Database Differences:
    - SQLite: Does not support READ ONLY transactions, uses PRAGMA for isolation
    - MySQL: Uses SET TRANSACTION before START TRANSACTION, supports READ ONLY (5.6.5+)
    - PostgreSQL: Full inline syntax (BEGIN ISOLATION LEVEL ... READ ONLY ... DEFERRABLE)
    """

    # ========== Capability Detection ==========

    def supports_transaction_mode(self) -> bool:
        """Whether transaction access mode (READ ONLY/READ WRITE) is supported.

        - PostgreSQL: True
        - MySQL: True (5.6.5+)
        - SQLite: False
        """
        ...  # pragma: no cover

    def supports_isolation_level_in_begin(self) -> bool:
        """Whether isolation level can be specified in BEGIN statement.

        - PostgreSQL: True (BEGIN ISOLATION LEVEL ...)
        - MySQL: False (uses SET TRANSACTION before START TRANSACTION)
        - SQLite: False (uses PRAGMA read_uncommitted)
        """
        ...  # pragma: no cover

    def supports_read_only_transaction(self) -> bool:
        """Whether READ ONLY transactions are supported.

        - PostgreSQL: True
        - MySQL: True (START TRANSACTION READ ONLY, 5.6.5+)
        - SQLite: False
        """
        ...  # pragma: no cover

    def supports_deferrable_transaction(self) -> bool:
        """Whether DEFERRABLE mode is supported.

        PostgreSQL-specific feature for SERIALIZABLE transactions.
        """
        ...  # pragma: no cover

    def supports_savepoint(self) -> bool:
        """Whether savepoints are supported.

        All major databases support savepoints.
        """
        ...  # pragma: no cover

    # ========== SQL Formatting ==========

    def format_begin_transaction(
        self, expr: "BeginTransactionExpression"
    ) -> Tuple[str, tuple]:
        """
        Format BEGIN TRANSACTION statement.

        Args:
            expr: BeginTransactionExpression with isolation level and mode.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Important:
            MUST return a SINGLE SQL statement. Multiple statements separated by
            semicolons are NOT allowed because backend.execute() only supports
            single-statement execution. For databases that require multiple
            statements (e.g., MySQL needs SET TRANSACTION before START TRANSACTION),
            the TransactionManager subclass should override _do_begin() to execute
            them separately.

        Note:
            - MySQL: Returns "START TRANSACTION" only; SET TRANSACTION is handled
              by MySQLTransactionManager._do_begin() separately.
            - PostgreSQL: Returns "BEGIN ISOLATION LEVEL ... READ ONLY ..." as single statement.
            - SQLite: Returns "BEGIN [DEFERRED|IMMEDIATE] TRANSACTION" as single statement.
        """
        ...  # pragma: no cover

    def format_commit_transaction(
        self, expr: "CommitTransactionExpression"
    ) -> Tuple[str, tuple]:
        """
        Format COMMIT statement.

        Args:
            expr: CommitTransactionExpression.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_rollback_transaction(
        self, expr: "RollbackTransactionExpression"
    ) -> Tuple[str, tuple]:
        """
        Format ROLLBACK statement.

        Args:
            expr: RollbackTransactionExpression with optional savepoint.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_savepoint(self, expr: "SavepointExpression") -> Tuple[str, tuple]:
        """
        Format SAVEPOINT statement.

        Args:
            expr: SavepointExpression with savepoint name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_release_savepoint(
        self, expr: "ReleaseSavepointExpression"
    ) -> Tuple[str, tuple]:
        """
        Format RELEASE SAVEPOINT statement.

        Args:
            expr: ReleaseSavepointExpression with savepoint name.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover

    def format_set_transaction(
        self, expr: "SetTransactionExpression"
    ) -> Tuple[str, tuple]:
        """
        Format SET TRANSACTION statement.

        Used primarily by MySQL to set isolation level before START TRANSACTION.

        Args:
            expr: SetTransactionExpression with isolation level and/or mode.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover
