# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

This dialect implements only the protocols for features that SQLite actually supports,
based on the SQLite version provided at initialization.
"""
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    CTESupport, FilterClauseSupport, WindowFunctionSupport, JSONSupport,
    ReturningSupport, AdvancedGroupingSupport, ArraySupport, ExplainSupport,
    GraphSupport, LockingSupport, MergeSupport, OrderedSetAggregationSupport,
    QualifyClauseSupport, TemporalTableSupport, UpsertSupport, LateralJoinSupport,
    WildcardSupport, JoinSupport, SetOperationSupport, ViewSupport,
    # DDL Protocols
    TableSupport, TruncateSupport, SchemaSupport, IndexSupport, SequenceSupport,
    TriggerSupport, GeneratedColumnSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CTEMixin, FilterClauseMixin, WindowFunctionMixin, JSONMixin, ReturningMixin,
    AdvancedGroupingMixin, ArrayMixin, ExplainMixin, GraphMixin, LockingMixin,
    MergeMixin, OrderedSetAggregationMixin, QualifyClauseMixin, TemporalTableMixin,
    UpsertMixin, LateralJoinMixin, JoinMixin, ViewMixin,
    # DDL Mixins
    TableMixin, TruncateMixin, SchemaMixin, IndexMixin, SequenceMixin,
    TriggerMixin, GeneratedColumnMixin,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from .protocols import SQLiteExtensionSupport, SQLitePragmaSupport
from .mixins import FTS5Mixin, SQLitePragmaMixin

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases
    from rhosocial.activerecord.backend.expression.advanced_functions import (
        ArrayExpression, OrderedSetAggregation
    )
    from rhosocial.activerecord.backend.expression.graph import MatchClause
    from rhosocial.activerecord.backend.expression.query_parts import (
        OrderByClause, LimitOffsetClause, ForUpdateClause, QualifyClause
    )
    from rhosocial.activerecord.backend.expression.statements import (
        CreateViewExpression, DropViewExpression,
        CreateMaterializedViewExpression, DropMaterializedViewExpression,
        RefreshMaterializedViewExpression, ReturningClause
    )


class SQLiteDialect(
    SQLDialectBase,
    # Include mixins for features that SQLite supports (with version-dependent implementations)
    CTEMixin, FilterClauseMixin, WindowFunctionMixin, JSONMixin, ReturningMixin,
    # Include mixins for features that SQLite does NOT support but need the methods to exist
    AdvancedGroupingMixin, ArrayMixin, ExplainMixin, GraphMixin, LockingMixin,
    MergeMixin, OrderedSetAggregationMixin, QualifyClauseMixin, TemporalTableMixin,
    UpsertMixin, LateralJoinMixin, JoinMixin, ViewMixin,
    # DDL Mixins
    TableMixin, TruncateMixin, SchemaMixin, IndexMixin, SequenceMixin,
    TriggerMixin, GeneratedColumnMixin,
    # SQLite-specific mixins
    FTS5Mixin, SQLitePragmaMixin,
    # Protocols for type checking
    CTESupport, FilterClauseSupport, WindowFunctionSupport, JSONSupport, ReturningSupport,
    AdvancedGroupingSupport, ArraySupport, ExplainSupport, GraphSupport, LockingSupport,
    MergeSupport, OrderedSetAggregationSupport, QualifyClauseSupport, TemporalTableSupport,
    UpsertSupport, LateralJoinSupport, WildcardSupport, JoinSupport, SetOperationSupport, ViewSupport,
    # DDL Protocols
    TableSupport, TruncateSupport, SchemaSupport, IndexSupport, SequenceSupport,
    TriggerSupport, GeneratedColumnSupport,
    # SQLite-specific protocols
    SQLiteExtensionSupport, SQLitePragmaSupport,
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
        self._runtime_params: Dict[str, Any] = {}
        super().__init__()

    def set_runtime_param(self, key: str, value: Any) -> None:
        """Set a runtime parameter (detected after connection)."""
        self._runtime_params[key] = value

    def get_runtime_param(self, key: str, default: Any = None) -> Any:
        """Get a runtime parameter."""
        return self._runtime_params.get(key, default)

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
        """MATERIALIZED hint is supported since SQLite 3.35.0."""
        return self.version >= (3, 35, 0)

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
        """JSON is supported with JSON1 extension.

        Detection logic:
        - SQLite >= 3.38.0: JSON1 is built-in, always available
        - SQLite < 3.38.0: Check runtime detection result (json1_available)
        """
        if self.version >= (3, 38, 0):
            return True
        # For older versions, use runtime detection result
        return self.get_runtime_param('json1_available', False)

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

    def supports_generated_columns(self) -> bool:
        """Whether generated columns are supported."""
        # Generated columns (STORED/VIRTUAL) are supported since SQLite 3.31.0
        return self.version >= (3, 31, 0)

    def supports_stored_generated_columns(self) -> bool:
        """Whether STORED generated columns are supported."""
        return self.supports_generated_columns()

    def supports_virtual_generated_columns(self) -> bool:
        """Whether VIRTUAL generated columns are supported."""
        return self.supports_generated_columns()

    # TableSupport protocol implementation
    def supports_create_table(self) -> bool:
        """Whether CREATE TABLE is supported."""
        return True

    def supports_drop_table(self) -> bool:
        """Whether DROP TABLE is supported."""
        return True

    def supports_alter_table(self) -> bool:
        """Whether ALTER TABLE is supported."""
        return True

    def supports_temporary_table(self) -> bool:
        """Whether TEMPORARY tables are supported."""
        return True

    def supports_if_not_exists_table(self) -> bool:
        """Whether CREATE TABLE IF NOT EXISTS is supported."""
        return True

    def supports_if_exists_table(self) -> bool:
        """Whether DROP TABLE IF EXISTS is supported."""
        return True

    def supports_rename_table(self) -> bool:
        """Whether RENAME TABLE is supported."""
        return True

    def supports_rename_column(self) -> bool:
        """Whether RENAME COLUMN is supported."""
        # RENAME COLUMN is supported since SQLite 3.25.0
        return self.version >= (3, 25, 0)

    def supports_drop_column(self) -> bool:
        """Whether DROP COLUMN is supported."""
        # DROP COLUMN is supported since SQLite 3.35.0
        return self.version >= (3, 35, 0)

    def supports_table_partitioning(self) -> bool:
        """Whether table partitioning is supported."""
        return False

    def supports_table_tablespace(self) -> bool:
        """Whether table tablespace is supported."""
        return False

    # IndexSupport protocol implementation
    def supports_create_index(self) -> bool:
        """Whether CREATE INDEX is supported."""
        return True

    def supports_drop_index(self) -> bool:
        """Whether DROP INDEX is supported."""
        return True

    def supports_unique_index(self) -> bool:
        """Whether UNIQUE indexes are supported."""
        return True

    def supports_index_if_exists(self) -> bool:
        """Whether DROP INDEX IF EXISTS is supported."""
        return True

    def supports_index_if_not_exists(self) -> bool:
        """Whether CREATE INDEX IF NOT EXISTS is supported."""
        return True

    def supports_partial_index(self) -> bool:
        """Whether partial indexes (WHERE clause) are supported."""
        # Partial indexes are supported since SQLite 3.8.0
        return self.version >= (3, 8, 0)

    def supports_functional_index(self) -> bool:
        """Whether functional/expression indexes are supported."""
        return True

    def supports_concurrent_index(self) -> bool:
        """Whether concurrent index creation is supported."""
        return False

    def supports_index_type(self) -> bool:
        """Whether index type (BTREE, HASH, etc.) is supported."""
        return False

    def supports_index_tablespace(self) -> bool:
        """Whether index tablespace is supported."""
        return False

    def supports_fulltext_index(self) -> bool:
        """Whether fulltext indexes are supported."""
        # SQLite uses FTS virtual tables instead of fulltext indexes
        return False

    def supports_fulltext_boolean_mode(self) -> bool:
        """Whether fulltext boolean mode is supported."""
        return False

    def supports_fulltext_parser(self) -> bool:
        """Whether custom fulltext parser is supported."""
        return False

    def supports_fulltext_query_expansion(self) -> bool:
        """Whether fulltext query expansion is supported."""
        return False

    def supports_index_include(self) -> bool:
        """Whether INCLUDE clause for indexes is supported."""
        return False

    # ILIKESupport protocol implementation
    def supports_ilike(self) -> bool:
        """Whether ILIKE (case-insensitive LIKE) is supported."""
        return False

    # SetOperationSupport protocol implementation
    def supports_union(self) -> bool:
        """Whether UNION operation is supported."""
        return True

    def supports_union_all(self) -> bool:
        """Whether UNION ALL operation is supported."""
        return True

    def supports_intersect(self) -> bool:
        """Whether INTERSECT operation is supported."""
        # INTERSECT is supported in SQLite since version 3.7.6 (2011-02-25)
        return self.version >= (3, 7, 6)

    def supports_except(self) -> bool:
        """Whether EXCEPT operation is supported."""
        # EXCEPT is supported in SQLite since version 3.7.6 (2011-02-25)
        return self.version >= (3, 7, 6)

    def supports_set_operation_order_by(self) -> bool:
        """Whether set operations support ORDER BY clauses."""
        return True

    def supports_set_operation_limit_offset(self) -> bool:
        """Whether set operations support LIMIT and OFFSET clauses."""
        return True

    def supports_set_operation_for_update(self) -> bool:
        """Whether set operations support FOR UPDATE clauses."""
        # SQLite doesn't support FOR UPDATE in set operations
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
        expr: "ArrayExpression"
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
        aggregation: "OrderedSetAggregation"
    ) -> Tuple[str, Tuple]:
        """
        Format ordered-set aggregation function call.

        Args:
            aggregation: OrderedSetAggregation object to format

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

    def format_wildcard(
        self,
        table: Optional[str] = None
    ) -> Tuple[str, Tuple]:
        """Format wildcard expression (* or table.*)."""
        if table:
            wildcard_sql = f'{self.format_identifier(table)}.*'
        else:
            wildcard_sql = '*'

        return wildcard_sql, ()

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
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        all_str = " ALL" if all_ else ""

        # Build the base set operation SQL
        base_sql = f"{left_sql} {operation}{all_str} {right_sql}"

        all_params = list(left_params + right_params)
        sql_parts = [base_sql]  # 移除了不必要的外层括号

        # Add alias if present
        if alias:
            sql_parts.append(f"AS {self.format_identifier(alias)}")

        # Add ORDER BY clause if present
        if order_by_clause:
            order_by_sql, order_by_params = order_by_clause.to_sql()
            sql_parts.append(order_by_sql)
            all_params.extend(order_by_params)

        # Add LIMIT/OFFSET clause if present
        if limit_offset_clause:
            limit_offset_sql, limit_offset_params = limit_offset_clause.to_sql()
            sql_parts.append(limit_offset_sql)
            all_params.extend(limit_offset_params)

        # Add FOR UPDATE clause if present (but SQLite doesn't support it in set operations)
        if for_update_clause:
            # Only add FOR UPDATE if the dialect supports it
            if self.supports_set_operation_for_update():
                for_update_sql, for_update_params = for_update_clause.to_sql()
                sql_parts.append(for_update_sql)
                all_params.extend(for_update_params)
            else:
                # If FOR UPDATE is requested but not supported, raise an error
                raise UnsupportedFeatureError(
                    self.name,
                    "FOR UPDATE in set operations",
                    "SQLite does not support FOR UPDATE clause in set operations (UNION, INTERSECT, EXCEPT)"
                )

        sql = " ".join(sql_parts)
        return sql, tuple(all_params)
    # endregion

    # region View Support (SQLite supports basic views but not materialized views)
    def supports_create_view(self) -> bool:
        """SQLite supports CREATE VIEW."""
        return True

    def supports_drop_view(self) -> bool:
        """SQLite supports DROP VIEW."""
        return True

    def supports_or_replace_view(self) -> bool:
        """SQLite supports CREATE VIEW IF NOT EXISTS (similar to OR REPLACE)."""
        return True

    def supports_temporary_view(self) -> bool:
        """SQLite supports TEMPORARY views."""
        return True

    def supports_materialized_view(self) -> bool:
        """SQLite does not support materialized views."""
        return False

    def supports_refresh_materialized_view(self) -> bool:
        """SQLite does not support REFRESH MATERIALIZED VIEW."""
        return False

    def supports_materialized_view_tablespace(self) -> bool:
        """SQLite does not support tablespace for materialized views."""
        return False

    def supports_materialized_view_storage_options(self) -> bool:
        """SQLite does not support storage options for materialized views."""
        return False

    def supports_if_exists_view(self) -> bool:
        """SQLite supports DROP VIEW IF EXISTS."""
        return True

    def supports_view_check_option(self) -> bool:
        """SQLite does not support WITH CHECK OPTION."""
        return False

    def supports_cascade_view(self) -> bool:
        """SQLite does not support CASCADE for DROP VIEW."""
        return False

    def format_create_view_statement(
        self,
        expr: "CreateViewExpression"
    ) -> Tuple[str, tuple]:
        """
        Format CREATE VIEW statement for SQLite.
        
        Note: SQLite does not allow parameters (placeholders like ?) in VIEW definitions.
        Any condition values must be inlined directly in the SQL string. Use RawSQLPredicate
        for conditions that need literal values instead of parameterized comparisons.
        
        Example:
            # Wrong - will fail with "parameters are not allowed in views"
            where=WhereClause(dialect, condition=Column(dialect, "status") == Literal(dialect, "active"))
            
            # Correct - use RawSQLPredicate to inline the value
            from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate
            where=WhereClause(dialect, condition=RawSQLPredicate(dialect, '"status" = \'active\''))
        """
        parts = ["CREATE"]
        if expr.temporary:
            parts.append("TEMPORARY")
        if expr.replace:
            parts.append("VIEW IF NOT EXISTS")
        else:
            parts.append("VIEW")
        parts.append(self.format_identifier(expr.view_name))

        if expr.column_aliases:
            cols = ', '.join(self.format_identifier(c) for c in expr.column_aliases)
            parts.append(f"({cols})")

        query_sql, query_params = expr.query.to_sql()
        parts.append(f"AS {query_sql}")

        # Warn if there are parameters - SQLite doesn't support them in views
        if query_params:
            import warnings
            warnings.warn(
                "SQLite does not allow parameters in VIEW definitions. "
                "The query contains parameters which will cause a runtime error. "
                "Use RawSQLPredicate to inline literal values instead.",
                UserWarning,
                stacklevel=3
            )

        return ' '.join(parts), query_params

    def format_drop_view_statement(
        self,
        expr: "DropViewExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP VIEW statement for SQLite."""
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.view_name))
        return ' '.join(parts), ()

    def format_create_materialized_view_statement(
        self,
        expr: "CreateMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format CREATE MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(
            self.name,
            "CREATE MATERIALIZED VIEW",
            "SQLite does not support materialized views. "
            "Consider using regular views or creating tables to store precomputed results."
        )

    def format_drop_materialized_view_statement(
        self,
        expr: "DropMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format DROP MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(
            self.name,
            "DROP MATERIALIZED VIEW",
            "SQLite does not support materialized views."
        )

    def format_refresh_materialized_view_statement(
        self,
        expr: "RefreshMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format REFRESH MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(
            self.name,
            "REFRESH MATERIALIZED VIEW",
            "SQLite does not support materialized views."
        )
    # endregion

    # region Trigger Support (SQLite supports triggers)
    def supports_trigger(self) -> bool:
        """SQLite supports triggers."""
        return True

    def supports_create_trigger(self) -> bool:
        """SQLite supports CREATE TRIGGER."""
        return True

    def supports_drop_trigger(self) -> bool:
        """SQLite supports DROP TRIGGER."""
        return True

    def supports_instead_of_trigger(self) -> bool:
        """SQLite supports INSTEAD OF triggers (for views)."""
        return True

    def supports_statement_trigger(self) -> bool:
        """SQLite does NOT support FOR EACH STATEMENT triggers."""
        return False

    def supports_trigger_referencing(self) -> bool:
        """SQLite supports referencing OLD and NEW rows."""
        return True

    def supports_trigger_when(self) -> bool:
        """SQLite supports WHEN condition in triggers."""
        return True

    def supports_trigger_if_not_exists(self) -> bool:
        """SQLite supports CREATE TRIGGER IF NOT EXISTS."""
        return True

    def format_create_trigger_statement(
        self,
        expr
    ):
        """Format CREATE TRIGGER statement for SQLite.

        SQLite trigger syntax:
        CREATE TRIGGER [IF NOT EXISTS] trigger_name
        {BEFORE | AFTER | INSTEAD OF}
        {DELETE | INSERT | UPDATE [OF column_list]} ON table_name
        [FOR EACH ROW] [WHEN condition]
        BEGIN ... END
        """
        from rhosocial.activerecord.backend.expression.statements import TriggerLevel

        parts = ["CREATE TRIGGER"]

        if expr.if_not_exists:
            parts.append("IF NOT EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        parts.append(expr.timing.value)

        if expr.update_columns:
            cols = ", ".join(self.format_identifier(c) for c in expr.update_columns)
            events_str = f"UPDATE OF {cols}"
        else:
            events_str = " OR ".join(e.value for e in expr.events)
        parts.append(events_str)

        parts.append("ON")
        parts.append(self.format_identifier(expr.table_name))

        if expr.level == TriggerLevel.ROW:
            parts.append("FOR EACH ROW")

        all_params = []
        if expr.condition:
            cond_sql, cond_params = expr.condition.to_sql()
            parts.append(f"WHEN ({cond_sql})")
            all_params.extend(cond_params)

        parts.append("BEGIN")
        parts.append(f"CALL {expr.function_name}();")
        parts.append("END")

        return " ".join(parts), tuple(all_params)

    def format_drop_trigger_statement(
        self,
        expr
    ):
        """Format DROP TRIGGER statement for SQLite."""
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()

    # region Generated Columns Support

    def format_column_definition(self, col_def) -> Tuple[str, tuple]:
        """Format a column definition for SQLite, including generated columns support."""
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType, GeneratedColumnType
        from rhosocial.activerecord.backend.expression import bases

        all_params = []

        # Basic column definition: name data_type
        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type}"

        # Handle constraints
        for constraint in col_def.constraints:
            if constraint.constraint_type == ColumnConstraintType.PRIMARY_KEY:
                col_sql += " PRIMARY KEY"
            elif constraint.constraint_type == ColumnConstraintType.NOT_NULL:
                col_sql += " NOT NULL"
            elif constraint.constraint_type == ColumnConstraintType.NULL:
                col_sql += " NULL"
            elif constraint.constraint_type == ColumnConstraintType.UNIQUE:
                col_sql += " UNIQUE"
            elif constraint.constraint_type == ColumnConstraintType.DEFAULT:
                if constraint.default_value is None:
                    raise ValueError("DEFAULT constraint must have a default value specified.")
                if isinstance(constraint.default_value, bases.BaseExpression):
                    default_sql, default_params = constraint.default_value.to_sql()
                    col_sql += f" DEFAULT {default_sql}"
                    all_params.extend(default_params)
                else:
                    col_sql += f" DEFAULT {self.get_parameter_placeholder()}"
                    all_params.append(constraint.default_value)
            elif constraint.constraint_type == ColumnConstraintType.CHECK and constraint.check_condition is not None:
                check_sql, check_params = constraint.check_condition.to_sql()
                col_sql += f" CHECK ({check_sql})"
                all_params.extend(check_params)
            elif constraint.constraint_type == ColumnConstraintType.FOREIGN_KEY:
                if constraint.foreign_key_reference is None:
                    raise ValueError("Foreign key constraint must have a foreign_key_reference specified.")
                referenced_table, referenced_columns = constraint.foreign_key_reference
                ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
                col_sql += f" REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})"

        # Handle generated columns (SQLite 3.31.0+)
        if col_def.generated_expression is not None:
            if not self.supports_generated_columns():
                raise UnsupportedFeatureError(
                    self.name,
                    "Generated columns",
                    "Generated columns require SQLite 3.31.0 or later."
                )

            gen_sql, gen_params = col_def.generated_expression.to_sql()
            all_params.extend(gen_params)

            col_sql += f" GENERATED ALWAYS AS ({gen_sql})"
            if col_def.generated_type == GeneratedColumnType.STORED:
                col_sql += " STORED"
            else:
                # Default to VIRTUAL if not specified
                col_sql += " VIRTUAL"

        return col_sql, tuple(all_params)

    # endregion
# endregion