# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

This dialect implements only the protocols for features that SQLite actually supports,
based on the SQLite version provided at initialization.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.expression.transaction import BeginTransactionExpression
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
    WildcardSupport,
    JoinSupport,
    SetOperationSupport,
    ViewSupport,
    # DDL Protocols
    TableSupport,
    ConstraintSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TriggerSupport,
    GeneratedColumnSupport,
    # Introspection Protocol
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
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
    JoinMixin,
    ViewMixin,
    # DDL Mixins
    TableMixin,
    ConstraintMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    GeneratedColumnMixin,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from .protocols import SQLiteExtensionSupport, SQLitePragmaSupport, SQLiteReindexSupport, SQLiteVirtualTableSupport
from .mixins import SQLitePragmaMixin, SQLiteIntrospectionCapabilityMixin, SQLiteVirtualTableMixin

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases
    from rhosocial.activerecord.backend.expression.advanced_functions import ArrayExpression, OrderedSetAggregation
    from rhosocial.activerecord.backend.expression.graph import MatchClause
    from rhosocial.activerecord.backend.expression.query_parts import (
        OrderByClause,
        LimitOffsetClause,
        ForUpdateClause,
        QualifyClause,
    )
    from rhosocial.activerecord.backend.expression.statements import (
        ExplainExpression,
        CreateViewExpression,
        DropViewExpression,
        CreateMaterializedViewExpression,
        DropMaterializedViewExpression,
        RefreshMaterializedViewExpression,
        ReturningClause,
        InsertExpression,
    )

# Module-level constants for error suggestions (SonarCloud S1192)
_SUGGESTION_ARRAY_TYPES = "SQLite does not support native array types. Consider using JSON or comma-separated values."
_SUGGESTION_JSON_TABLE = (
    "SQLite does not support JSON_TABLE. Consider using json_each() or json_extract() with subqueries."
)
_SUGGESTION_GRAPH_MATCH = "SQLite does not support graph MATCH clause."
_SUGGESTION_ORDERED_SET_AGG = "SQLite does not support ordered-set aggregate functions (WITHIN GROUP)."
_SUGGESTION_QUALIFY = "SQLite does not support QUALIFY clause. Use a subquery or CTE instead."
_SUGGESTION_MATERIALIZED_VIEW = "SQLite does not support materialized views."
_SUGGESTION_MATERIALIZED_VIEW_ALT = (
    "SQLite does not support materialized views. Consider using regular views "
    "or creating tables to store precomputed results."
)
_SUGGESTION_FOR_UPDATE_SET_OP = "SQLite does not support FOR UPDATE clause in set operations (UNION, INTERSECT, EXCEPT)"


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
    JoinMixin,
    ViewMixin,
    # DDL Mixins
    TableMixin,
    ConstraintMixin,
    TruncateMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    TriggerMixin,
    GeneratedColumnMixin,
    # SQLite-specific mixins
    SQLitePragmaMixin,
    SQLiteIntrospectionCapabilityMixin,
    SQLiteVirtualTableMixin,
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
    WildcardSupport,
    JoinSupport,
    SetOperationSupport,
    ViewSupport,
    # DDL Protocols
    TableSupport,
    ConstraintSupport,
    TruncateSupport,
    SchemaSupport,
    IndexSupport,
    SequenceSupport,
    TriggerSupport,
    GeneratedColumnSupport,
    # SQLite-specific protocols
    SQLiteExtensionSupport,
    SQLitePragmaSupport,
    SQLiteVirtualTableSupport,
    SQLiteReindexSupport,
    # Introspection Protocol
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
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

    def get_parameter_placeholder(self, _position: int = 0) -> str:
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
        return self.get_runtime_param("json1_available", False)

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

    def format_explain_statement(self, expr: "ExplainExpression") -> Tuple[str, tuple]:
        """Format EXPLAIN / EXPLAIN QUERY PLAN for SQLite.

        SQLite supports two forms:
        - ``EXPLAIN <stmt>``         — shows the bytecode program
        - ``EXPLAIN QUERY PLAN <stmt>`` — shows the query strategy

        ExplainType.QUERY_PLAN maps to the second form; all other types
        (and the default None) use the first form.  The ``analyze`` flag is
        not meaningful for SQLite and is silently ignored.
        """
        from rhosocial.activerecord.backend.expression.statements import ExplainType
        statement_sql, statement_params = expr.statement.to_sql()
        options = expr.options
        if (
            options is not None
            and hasattr(options, "type")
            and options.type == ExplainType.QUERY_PLAN
        ):
            return f"EXPLAIN QUERY PLAN {statement_sql}", statement_params
        return f"EXPLAIN {statement_sql}", statement_params

    def supports_graph_match(self) -> bool:
        """Whether graph query MATCH clause is supported."""
        return False

    def supports_for_update_skip_locked(self) -> bool:
        """Whether FOR UPDATE SKIP LOCKED is supported."""
        return False

    def supports_for_update(self) -> bool:
        """Whether FOR UPDATE clause is supported in SELECT statements.

        SQLite does not support FOR UPDATE as it uses database-level locking
        (SHARED, RESERVED, PENDING, EXCLUSIVE) rather than row-level locking.
        For write serialization, use BEGIN IMMEDIATE or BEGIN EXCLUSIVE transactions.
        """
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

    def format_insert_statement(self, expr: "InsertExpression") -> Tuple[str, tuple]:
        """Format INSERT statement with SQLite-specific OR REPLACE / OR IGNORE support.

        SQLite supports two alternative INSERT syntaxes in addition to the standard
        ON CONFLICT clause:

        - INSERT OR REPLACE INTO ...: Deletes the existing row and inserts the new one.
        - INSERT OR IGNORE INTO ...: Silently skips rows that would cause constraint violations.

        These are controlled via the ``dialect_options`` dict on InsertExpression:

        - ``{'or_replace': True}``  ->  INSERT OR REPLACE INTO ...
        - ``{'or_ignore': True}``   ->  INSERT OR IGNORE INTO ...

        When neither option is set, the standard INSERT INTO ... syntax is used
        (with ON CONFLICT / RETURNING appended as appropriate).
        """
        or_replace = expr.dialect_options.get('or_replace', False)
        or_ignore = expr.dialect_options.get('or_ignore', False)

        if or_replace and or_ignore:
            raise ValueError(
                "Cannot specify both 'or_replace' and 'or_ignore' in dialect_options."
            )
        if (or_replace or or_ignore) and expr.on_conflict is not None:
            raise ValueError(
                "Cannot use 'or_replace'/'or_ignore' together with 'on_conflict'. "
                "Use either the SQLite-specific OR REPLACE/IGNORE syntax or the "
                "standard ON CONFLICT clause, but not both."
            )

        # Perform strict parameter validation
        if self.strict_validation:
            expr.validate(strict=True)

        all_params: List[Any] = []
        table_sql, table_params = expr.into.to_sql()
        all_params.extend(table_params)

        columns_sql = ""
        if expr.columns:
            columns_sql = "(" + ", ".join([self.format_identifier(c) for c in expr.columns]) + ")"

        source_sql = ""
        # Import here to avoid circular imports
        from rhosocial.activerecord.backend.expression.statements import (
            DefaultValuesSource,
            ValuesSource,
            SelectSource,
        )

        if isinstance(expr.source, DefaultValuesSource):
            source_sql = "DEFAULT VALUES"
        elif isinstance(expr.source, ValuesSource):
            all_rows_sql = []
            for row in expr.source.values_list:
                row_sql, row_params = [], []
                for val in row:
                    s, p = val.to_sql()
                    row_sql.append(s)
                    row_params.extend(p)
                all_rows_sql.append(f"({', '.join(row_sql)})")
                all_params.extend(row_params)
            source_sql = "VALUES " + ", ".join(all_rows_sql)
        elif isinstance(expr.source, SelectSource):
            s_sql, s_params = expr.source.select_query.to_sql()
            source_sql = s_sql
            all_params.extend(s_params)

        # Build the INSERT keyword with optional OR qualifier
        if or_replace:
            sql = f"INSERT OR REPLACE INTO {table_sql} {columns_sql} {source_sql}".strip()
        elif or_ignore:
            sql = f"INSERT OR IGNORE INTO {table_sql} {columns_sql} {source_sql}".strip()
        else:
            sql = f"INSERT INTO {table_sql} {columns_sql} {source_sql}".strip()

        # ON CONFLICT clause (only when not using OR REPLACE/IGNORE)
        if expr.on_conflict:
            conflict_sql, conflict_params = expr.on_conflict.to_sql()
            sql += f" {conflict_sql}"
            all_params.extend(conflict_params)

        # RETURNING clause
        if expr.returning:
            returning_sql, returning_params = self.format_returning_clause(expr.returning)
            sql += f" {returning_sql}"
            all_params.extend(returning_params)

        return sql, tuple(all_params)

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

    # ConstraintSupport protocol implementation
    # SQLite 3.53.0+ supports ALTER TABLE ADD/DROP CONSTRAINT for NOT NULL and CHECK
    def supports_add_constraint(self) -> bool:
        """Whether ALTER TABLE ADD CONSTRAINT is supported.

        SQLite 3.53.0+ supports adding NOT NULL and CHECK constraints via ALTER TABLE.

        Returns:
            True if SQLite version >= 3.53.0, False otherwise.
        """
        return self.version >= (3, 53, 0)

    def supports_drop_constraint(self) -> bool:
        """Whether ALTER TABLE DROP CONSTRAINT is supported.

        SQLite 3.53.0+ supports dropping NOT NULL and CHECK constraints via ALTER TABLE.

        Returns:
            True if SQLite version >= 3.53.0, False otherwise.
        """
        return self.version >= (3, 53, 0)

    def supports_fk_match(self) -> bool:
        """SQLite does not support MATCH clause in FOREIGN KEY."""
        return False

    def supports_deferrable_constraint(self) -> bool:
        """SQLite does not support DEFERRABLE table constraints."""
        return False

    def supports_constraint_enforced(self) -> bool:
        """SQLite does not support ENFORCED/NOT ENFORCED constraint control."""
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
        self, operation: str, _expressions: List["bases.BaseExpression"]
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
            self.name, f"{operation} grouping operation", f"{operation} is not supported by SQLite."
        )

    def format_array_expression(self, _expr: "ArrayExpression") -> Tuple[str, Tuple]:
        """Format array expression."""
        # SQLite does not support native array types
        raise UnsupportedFeatureError(self.name, "Array operations", _SUGGESTION_ARRAY_TYPES)

    def format_json_table_expression(
        self, _json_col_sql: str, _path: str, _columns: List[Dict[str, Any]], _alias: Optional[str], _params: tuple
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
        raise UnsupportedFeatureError(self.name, "JSON_TABLE function", _SUGGESTION_JSON_TABLE)

    def format_match_clause(self, _clause: "MatchClause") -> Tuple[str, tuple]:
        """
        Format MATCH clause with expression.

        Args:
            clause: MatchClause object containing the match expression

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted clause.
        """
        # SQLite does not support graph MATCH clause
        raise UnsupportedFeatureError(self.name, "graph MATCH clause", _SUGGESTION_GRAPH_MATCH)

    def format_match_predicate(
        self,
        table: str,
        query: str,
        columns: Optional[List[str]] = None,
        negate: bool = False,
    ) -> Tuple[str, tuple]:
        """Format full-text search MATCH predicate for FTS5.

        SQLite supports the MATCH operator for full-text search via FTS5
        virtual tables. This method generates the parameterized MATCH
        expression by delegating to the FTS5 extension.

        Args:
            table: Name of the FTS5 virtual table
            query: Full-text search query string
            columns: Specific columns to search (None for all columns)
            negate: If True, negate the match (NOT MATCH)

        Returns:
            Tuple of (SQL string, parameters tuple)
        """
        return self.format_fts5_match_expression(
            table_name=table,
            query=query,
            columns=columns,
            negate=negate,
        )

    def format_ordered_set_aggregation(self, _aggregation: "OrderedSetAggregation") -> Tuple[str, Tuple]:
        """
        Format ordered-set aggregation function call.

        Args:
            aggregation: OrderedSetAggregation object to format

        Returns:
            Tuple of (SQL string, parameters tuple) for the formatted expression.
        """
        # SQLite does not support ordered-set aggregate functions
        raise UnsupportedFeatureError(self.name, "ordered-set aggregate functions", _SUGGESTION_ORDERED_SET_AGG)

    def format_qualify_clause(self, _clause: "QualifyClause") -> Tuple[str, tuple]:
        """Format QUALIFY clause."""
        # SQLite does not support QUALIFY clause
        raise UnsupportedFeatureError(self.name, "QUALIFY clause", _SUGGESTION_QUALIFY)

    def format_returning_clause(self, clause: "ReturningClause") -> Tuple[str, tuple]:
        """Format RETURNING clause."""
        # Check if the dialect supports returning clause
        if not self.supports_returning_clause():
            raise UnsupportedFeatureError(
                self.name, "RETURNING clause", "Use a separate SELECT statement to retrieve the affected data."
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

    def format_wildcard(self, table: Optional[str] = None) -> Tuple[str, Tuple]:
        """Format wildcard expression (* or table.*)."""
        if table:
            wildcard_sql = f"{self.format_identifier(table)}.*"
        else:
            wildcard_sql = "*"

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
        for_update_clause: Optional["ForUpdateClause"] = None,
    ) -> Tuple[str, Tuple]:
        """Format set operation expression (UNION, INTERSECT, EXCEPT)."""
        left_sql, left_params = left.to_sql()
        right_sql, right_params = right.to_sql()
        all_str = " ALL" if all_ else ""

        # Build the base set operation SQL
        base_sql = f"{left_sql} {operation}{all_str} {right_sql}"

        all_params = list(left_params + right_params)
        sql_parts = [base_sql]  # removed unnecessary outer parentheses

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
                raise UnsupportedFeatureError(self.name, "FOR UPDATE in set operations", _SUGGESTION_FOR_UPDATE_SET_OP)

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

    def format_create_view_statement(self, expr: "CreateViewExpression") -> Tuple[str, tuple]:
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
            cols = ", ".join(self.format_identifier(c) for c in expr.column_aliases)
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
                stacklevel=3,
            )

        return " ".join(parts), query_params

    def format_drop_view_statement(self, expr: "DropViewExpression") -> Tuple[str, tuple]:
        """Format DROP VIEW statement for SQLite."""
        parts = ["DROP VIEW"]
        if expr.if_exists:
            parts.append("IF EXISTS")
        parts.append(self.format_identifier(expr.view_name))
        return " ".join(parts), ()

    def format_create_materialized_view_statement(self, _expr: "CreateMaterializedViewExpression") -> Tuple[str, tuple]:
        """Format CREATE MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(self.name, "CREATE MATERIALIZED VIEW", _SUGGESTION_MATERIALIZED_VIEW_ALT)

    def format_drop_materialized_view_statement(self, _expr: "DropMaterializedViewExpression") -> Tuple[str, tuple]:
        """Format DROP MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(self.name, "DROP MATERIALIZED VIEW", _SUGGESTION_MATERIALIZED_VIEW)

    def format_refresh_materialized_view_statement(
        self, _expr: "RefreshMaterializedViewExpression"
    ) -> Tuple[str, tuple]:
        """Format REFRESH MATERIALIZED VIEW statement - not supported by SQLite."""
        raise UnsupportedFeatureError(self.name, "REFRESH MATERIALIZED VIEW", _SUGGESTION_MATERIALIZED_VIEW)

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

    def format_create_trigger_statement(self, expr):
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

    def format_drop_trigger_statement(self, expr):
        """Format DROP TRIGGER statement for SQLite."""
        parts = ["DROP TRIGGER"]

        if expr.if_exists:
            parts.append("IF EXISTS")

        parts.append(self.format_identifier(expr.trigger_name))

        return " ".join(parts), ()

    # region Generated Columns Support

    def _handle_primary_key_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle PRIMARY KEY constraint formatting."""
        return " PRIMARY KEY", ()

    def _handle_not_null_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle NOT NULL constraint formatting."""
        return " NOT NULL", ()

    def _handle_null_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle NULL constraint formatting."""
        return " NULL", ()

    def _handle_unique_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle UNIQUE constraint formatting."""
        return " UNIQUE", ()

    def _handle_default_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle DEFAULT constraint formatting."""
        from rhosocial.activerecord.backend.expression import bases

        if constraint.default_value is None:
            raise ValueError("DEFAULT constraint must have a default value specified.")
        if isinstance(constraint.default_value, bases.BaseExpression):
            default_sql, default_params = constraint.default_value.to_sql()
            return f" DEFAULT {default_sql}", default_params
        return f" DEFAULT {self.get_parameter_placeholder()}", (constraint.default_value,)

    def _handle_check_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle CHECK constraint formatting."""
        if constraint.check_condition is None:
            return "", ()
        check_sql, check_params = constraint.check_condition.to_sql()
        return f" CHECK ({check_sql})", check_params

    def _handle_foreign_key_constraint(self, constraint) -> Tuple[str, tuple]:
        """Handle FOREIGN KEY constraint formatting."""
        from rhosocial.activerecord.backend.expression.statements import ReferentialAction

        if constraint.foreign_key_reference is None:
            raise ValueError("Foreign key constraint must have a foreign_key_reference specified.")
        referenced_table, referenced_columns = constraint.foreign_key_reference
        ref_cols_str = ", ".join(self.format_identifier(col) for col in referenced_columns)
        result = f" REFERENCES {self.format_identifier(referenced_table)}({ref_cols_str})"

        # ON DELETE / ON UPDATE (SQLite fully supports all referential actions)
        if constraint.on_delete is not None and constraint.on_delete != ReferentialAction.NO_ACTION:
            result += f" ON DELETE {constraint.on_delete.value}"
        if constraint.on_update is not None and constraint.on_update != ReferentialAction.NO_ACTION:
            result += f" ON UPDATE {constraint.on_update.value}"

        return result, ()

    def _handle_generated_column(self, col_def) -> Tuple[str, tuple]:
        """Handle generated column formatting."""
        from rhosocial.activerecord.backend.expression.statements import GeneratedColumnType

        if not self.supports_generated_columns():
            raise UnsupportedFeatureError(
                self.name, "Generated columns", "Generated columns require SQLite 3.31.0 or later."
            )
        gen_sql, gen_params = col_def.generated_expression.to_sql()
        gen_type = " STORED" if col_def.generated_type == GeneratedColumnType.STORED else " VIRTUAL"
        return f" GENERATED ALWAYS AS ({gen_sql}){gen_type}", gen_params

    def format_column_definition(self, col_def) -> Tuple[str, tuple]:
        """Format a column definition for SQLite, including generated columns support.

        Uses a strategy pattern with dictionary dispatch to handle different constraint
        types, reducing cognitive complexity compared to if-elif chains.
        """
        from rhosocial.activerecord.backend.expression.statements import ColumnConstraintType

        # Constraint handler mapping for dispatch
        constraint_handlers = {
            ColumnConstraintType.PRIMARY_KEY: self._handle_primary_key_constraint,
            ColumnConstraintType.NOT_NULL: self._handle_not_null_constraint,
            ColumnConstraintType.NULL: self._handle_null_constraint,
            ColumnConstraintType.UNIQUE: self._handle_unique_constraint,
            ColumnConstraintType.DEFAULT: self._handle_default_constraint,
            ColumnConstraintType.CHECK: self._handle_check_constraint,
            ColumnConstraintType.FOREIGN_KEY: self._handle_foreign_key_constraint,
        }

        all_params = []

        # Basic column definition: name data_type
        col_sql = f"{self.format_identifier(col_def.name)} {col_def.data_type}"

        # Handle constraints using dispatch table
        for constraint in col_def.constraints:
            handler = constraint_handlers.get(constraint.constraint_type)
            if handler:
                sql_part, params = handler(constraint)
                col_sql += sql_part
                all_params.extend(params)

        # Handle generated columns (SQLite 3.31.0+)
        if col_def.generated_expression is not None:
            gen_sql, gen_params = self._handle_generated_column(col_def)
            col_sql += gen_sql
            all_params.extend(gen_params)

        return col_sql, tuple(all_params)

    # region Transaction Control

    def supports_transaction_mode(self) -> bool:
        """SQLite does not support READ ONLY transactions.

        SQLite transactions are always read-write by default.
        There's no SQL syntax to specify READ ONLY mode.
        """
        return False

    def supports_isolation_level_in_begin(self) -> bool:
        """SQLite does not support isolation level in BEGIN statement.

        SQLite uses PRAGMA read_uncommitted to control isolation,
        not the BEGIN statement syntax.
        """
        return False

    def supports_read_only_transaction(self) -> bool:
        """SQLite does not support READ ONLY transactions.

        While SQLite supports read-only database connections at the OS level,
        it does not support the SQL-level READ ONLY transaction mode.
        """
        return False

    def supports_deferrable_transaction(self) -> bool:
        """SQLite does not support DEFERRABLE mode.

        DEFERRABLE is PostgreSQL-specific for SERIALIZABLE transactions.
        """
        return False

    def supports_savepoint(self) -> bool:
        """SQLite supports savepoints.

        SQLite has full support for SAVEPOINT, RELEASE SAVEPOINT,
        and ROLLBACK TO SAVEPOINT.
        """
        return True

    def format_begin_transaction(
        self, expr: "BeginTransactionExpression"
    ) -> Tuple[str, tuple]:
        """Format BEGIN TRANSACTION statement for SQLite.

        SQLite uses BEGIN {DEFERRED|IMMEDIATE|EXCLUSIVE} TRANSACTION syntax.
        Isolation level is controlled via PRAGMA read_uncommitted.
        READ ONLY mode is NOT supported - raises error if requested.

        Args:
            expr: BeginTransactionExpression with isolation level and mode.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedTransactionModeError: If READ ONLY mode is requested.
        """
        from rhosocial.activerecord.backend.errors import UnsupportedTransactionModeError
        from rhosocial.activerecord.backend.transaction import IsolationLevel, TransactionMode

        params = expr.get_params()
        mode = params.get("mode")

        # Check for unsupported features
        if mode == TransactionMode.READ_ONLY:
            raise UnsupportedTransactionModeError(
                feature="READ ONLY transactions",
                backend="SQLite",
                message="Consider using a separate read-only database connection."
            )

        # Check for explicit begin_type (SQLite-specific)
        # This allows direct control over DEFERRED/IMMEDIATE/EXCLUSIVE modes
        begin_type = params.get("begin_type")
        if begin_type is not None:
            valid_types = ("DEFERRED", "IMMEDIATE", "EXCLUSIVE")
            bt_upper = begin_type.upper()
            if bt_upper not in valid_types:
                raise ValueError(
                    f"Invalid SQLite begin type: {begin_type}. Must be one of {valid_types}"
                )
            return f"BEGIN {bt_upper} TRANSACTION", ()

        # Map isolation level to BEGIN type
        # SQLite's default is SERIALIZABLE, DEFERRED gives READ_UNCOMMITTED via PRAGMA
        isolation = params.get("isolation_level")

        if isolation == IsolationLevel.READ_UNCOMMITTED:
            # Use DEFERRED + PRAGMA read_uncommitted = 1
            # Note: PRAGMA must be executed separately by the transaction manager
            return "BEGIN DEFERRED TRANSACTION", ()
        else:
            # Default to IMMEDIATE for better concurrency
            return "BEGIN IMMEDIATE TRANSACTION", ()

    # endregion

    # region SQLite-specific statements

    # SQLite function version support: function_name -> (min_version, max_version)
    # min_version: minimum supported version (inclusive), None = all versions
    # max_version: maximum supported version (inclusive), None = no upper limit
    # Reference: https://www.sqlite.org/changes.html
    _SQLITE_FUNCTION_VERSIONS = {
        # JSON functions - SQLite 3.38.0+ (JSON1 built-in), but functions available via extension earlier
        "json": (None, None),  # Available since early versions with JSON1 extension
        "json_array": (None, None),
        "json_object": (None, None),
        "json_extract": (None, None),
        "json_type": (None, None),
        "json_valid": (None, None),
        "json_quote": (None, None),
        "json_remove": (None, None),
        "json_set": (None, None),
        "json_insert": (None, None),
        "json_replace": (None, None),
        "json_patch": (None, None),  # RFC 7396 MergePatch
        "json_array_length": (None, None),
        "json_array_unpack": (None, None),  # Custom wrapper
        "json_object_pack": (None, None),  # Custom wrapper
        "json_object_retrieve": (None, None),  # Custom wrapper
        "json_object_length": (None, None),
        "json_object_keys": (None, None),
        "json_tree": (None, None),  # Table-valued function
        "json_each": (None, None),  # Table-valued function
        "json_array_insert": ((3, 53, 0), None),  # Added in 3.53.0
        "jsonb_array_insert": ((3, 53, 0), None),  # Added in 3.53.0
        # String functions - available since early versions
        "substr": (None, None),
        "instr": (None, None),  # Added in 3.7.6
        "printf": (None, None),
        "unicode": (None, None),
        "hex": (None, None),
        "unhex": ((3, 45, 0), None),  # Added in 3.45.0
        "soundex": (None, None),  # Requires SQLITE_SOUNDEX compile option
        "group_concat": (None, None),
        "trim_sqlite": (None, None),
        "ltrim": (None, None),
        "rtrim": (None, None),
        # Date/Time functions - available since early versions
        "date_func": (None, None),
        "time_func": (None, None),
        "datetime_func": (None, None),
        "julianday": (None, None),
        "strftime_func": (None, None),
        # Math functions - available since early versions
        "random_func": (None, None),
        "abs_sql": (None, None),
        "sign": ((3, 21, 0), None),  # Added in 3.21.0
        "total": (None, None),
        # Math enhanced functions
        "round_": (None, None),
        "pow": ((3, 35, 0), None),  # Added in 3.35.0
        "power": ((3, 35, 0), None),  # Alias for pow
        "sqrt": ((3, 35, 0), None),  # Added in 3.35.0
        "mod": ((3, 35, 0), None),  # Added in 3.35.0
        "ceil": ((3, 35, 0), None),  # Added in 3.35.0
        "floor": ((3, 35, 0), None),  # Added in 3.35.0
        "trunc": ((3, 35, 0), None),  # Added in 3.35.0
        "max_": (None, None),
        "min_": (None, None),
        "avg": (None, None),
        # BLOB functions
        "zeroblob": (None, None),
        "randomblob": (None, None),
        # System functions
        "typeof": (None, None),
        "quote": (None, None),
        "last_insert_rowid": (None, None),
        "changes": (None, None),
        # Conditional functions
        "iif": ((3, 32, 0), None),  # Added in 3.32.0
    }

    def supports_functions(self) -> Dict[str, bool]:
        """Return supported SQL functions as function_name -> bool mapping.

        This method combines:
        1. Core functions from rhosocial.activerecord.backend.expression.functions
        2. SQLite-specific functions from rhosocial.activerecord.backend.impl.sqlite.functions

        SQLite version-specific functions:
        - json_array_insert, jsonb_array_insert: SQLite 3.53.0+
        - sign: SQLite 3.21.0+
        - pow, power, sqrt, mod, ceil, floor, trunc: SQLite 3.35.0+
        - unhex: SQLite 3.45.0+
        - iif: SQLite 3.32.0+

        Returns:
        Dict mapping function names to True (supported) or False.
        """
        from rhosocial.activerecord.backend.expression.functions import (
            __all__ as core_functions,
        )
        from rhosocial.activerecord.backend.impl.sqlite import functions as sqlite_functions

        result = {}
        for func_name in core_functions:
            result[func_name] = True

        sqlite_funcs = getattr(sqlite_functions, "__all__", [])
        for func_name in sqlite_funcs:
            result[func_name] = self._is_sqlite_function_supported(func_name)

        return result

    def _is_sqlite_function_supported(self, func_name: str) -> bool:
        """Check if a SQLite-specific function is supported based on version.

        Args:
            func_name: Name of the SQLite function

        Returns:
            True if supported, False otherwise
        """
        version_range = self._SQLITE_FUNCTION_VERSIONS.get(func_name)
        if version_range is None:
            return True

        min_version, max_version = version_range

        if min_version is not None and self.version < min_version:
            return False

        if max_version is not None and self.version > max_version:
            return False

        return True

    def supports_reindex(self) -> bool:
        """SQLite supports REINDEX statement."""
        return True

    def supports_reindex_expressions(self) -> bool:
        """SQLite 3.53.0+ supports REINDEX EXPRESSIONS."""
        return self.version >= (3, 53, 0)

    def format_reindex_statement(self, expr) -> Tuple[str, tuple]:
        """Format REINDEX statement for SQLite.

        SQLite REINDEX syntax:
        - REINDEX                          -- Rebuild all indexes
        - REINDEX table_name               -- Rebuild all indexes on table
        - REINDEX index_name               -- Rebuild specific index
        - REINDEX EXPRESSIONS              -- Rebuild all expression indexes (3.53.0+)

        Args:
            expr: SQLiteReindexExpression object

        Returns:
            Tuple of (SQL string, empty parameters tuple)

        Raises:
            UnsupportedFeatureError: If REINDEX EXPRESSIONS is requested on
                SQLite versions below 3.53.0.
        """
        if expr.expressions:
            if not self.supports_reindex_expressions():
                raise UnsupportedFeatureError(
                    self.name,
                    "REINDEX EXPRESSIONS",
                    "REINDEX EXPRESSIONS requires SQLite 3.53.0 or later."
                )
            return "REINDEX EXPRESSIONS", ()

        if expr.index_name:
            return f"REINDEX {self.format_identifier(expr.index_name)}", ()

        if expr.table_name:
            return f"REINDEX {self.format_identifier(expr.table_name)}", ()

        return "REINDEX", ()

    # endregion


# endregion
