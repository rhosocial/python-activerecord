# src/rhosocial/activerecord/backend/impl/sqlite/dialect.py
"""
SQLite backend SQL dialect implementation.

This dialect implements only the protocols for features that SQLite actually supports,
based on the SQLite version provided at initialization.
"""

from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.protocols import (
    CollationSupport,
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
    # Type Support Protocol
    DDLTypeSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    CollationMixin,
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
    # DDL Mixins
    TableMixin,
    ConstraintMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    GeneratedColumnMixin,
    PartitionMixin,
    # New Mixins
    PredicateMixin,
    ExpressionMixin,
    DQLMixin,
    IdentifierMixin,
    DateTimeMixin,
    DDLColumnMixin,
    DMLMixin,
    TransactionControlMixin,
    ViewMixin,
    TriggerMixin,
    SetOperationMixin,
)
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression import bases
    from rhosocial.activerecord.backend.expression.advanced_functions import ArrayExpression, OrderedSetAggregation
    from rhosocial.activerecord.backend.expression.graph import MatchClause
    from rhosocial.activerecord.backend.expression.query_parts import QualifyClause
    from rhosocial.activerecord.backend.expression.statements import ExplainExpression
    from rhosocial.activerecord.backend.expression.statements.ddl_truncate import TruncateExpression

from .protocols import (
    SQLiteExtensionSupport,
    SQLitePragmaSupport,
    SQLiteReindexSupport,
    SQLiteVirtualTableSupport,
    SQLiteFTS5Support,
    SQLiteRTreeSupport,
    SQLiteGeopolySupport,
    SQLiteJSON1Support,
    SQLiteMaintenanceSupport,
)
from .mixins import (
    SQLitePragmaMixin,
    SQLiteIntrospectionCapabilityMixin,
    SQLiteVirtualTableMixin,
    SQLiteReindexMixin,
    SQLiteMaintenanceMixin,
    SQLiteIdentifierMixin,
    SQLiteDateTimeMixin,
    SQLiteDDLColumnMixin,
    SQLiteDMLMixin,
    SQLiteSetOperationMixin,
    SQLiteViewMixin,
    SQLiteTriggerMixin,
    SQLiteTransactionMixin,
    SQLiteFunctionMixin,
    SQLiteFTS5Mixin,
    SQLiteRTreeMixin,
    SQLiteGeopolyMixin,
    SQLiteTypeSupportMixin,
)

# Module-level constants for error suggestions (SonarCloud S1192)
_SUGGESTION_ARRAY_TYPES = "SQLite does not support native array types. Consider using JSON or comma-separated values."
_SUGGESTION_JSON_TABLE = (
    "SQLite does not support JSON_TABLE. Consider using json_each() or json_extract() with subqueries."
)
_SUGGESTION_GRAPH_MATCH = "SQLite does not support graph MATCH clause."
_SUGGESTION_ORDERED_SET_AGG = "SQLite does not support ordered-set aggregate functions (WITHIN GROUP)."
_SUGGESTION_QUALIFY = "SQLite does not support QUALIFY clause. Use a subquery or CTE instead."


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
    # DDL Mixins (without SQLite overrides)
    TableMixin,
    ConstraintMixin,
    SchemaMixin,
    IndexMixin,
    SequenceMixin,
    GeneratedColumnMixin,
    PartitionMixin,
    # New Mixins (without SQLite overrides)
    PredicateMixin,
    ExpressionMixin,
    DQLMixin,
    # SQLite-specific mixins (BEFORE generic mixins they override)
    SQLiteTransactionMixin,
    SQLiteIdentifierMixin,
    SQLiteDateTimeMixin,
    SQLiteDDLColumnMixin,
    SQLiteDMLMixin,
    SQLiteSetOperationMixin,
    SQLiteViewMixin,
    SQLiteTriggerMixin,
    SQLitePragmaMixin,
    SQLiteIntrospectionCapabilityMixin,
    SQLiteVirtualTableMixin,
    SQLiteReindexMixin,
    SQLiteMaintenanceMixin,
    SQLiteFunctionMixin,
    # Extension expression mixins
    SQLiteFTS5Mixin,
    SQLiteRTreeMixin,
    SQLiteGeopolyMixin,
    # DataType formatting and parsing
    SQLiteTypeSupportMixin,
    # Collation mixin (after SQLite mixins so that SQLiteDateTimeMixin.supports_collate_expression takes priority)
    CollationMixin,
    # Generic mixins (fallback for methods not overridden by SQLite)
    IdentifierMixin,
    DateTimeMixin,
    DDLColumnMixin,
    DMLMixin,
    TransactionControlMixin,
    ViewMixin,
    TriggerMixin,
    SetOperationMixin,
    # Protocols for type checking
    CollationSupport,
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
    SQLiteFTS5Support,
    SQLiteRTreeSupport,
    SQLiteGeopolySupport,
    SQLiteJSON1Support,
    SQLiteMaintenanceSupport,
    # Introspection Protocol
    IntrospectionSupport,
    # Transaction Control Protocol
    TransactionControlSupport,
    # Function Support Protocol
    SQLFunctionSupport,
    # DataType Support Protocol
    DDLTypeSupport,
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

    def __init__(self, version: Optional[Tuple[int, int, int]] = None):
        """
        Initialize SQLite dialect with specific version.

        Args:
            version: SQLite version tuple (major, minor, patch).
                If None, the dialect must be adapted via
                backend.introspect_and_adapt() before version-dependent
                features can be used.
        """
        super().__init__()
        if version is not None:
            self.version = version
        self._runtime_params: Dict[str, Any] = {}

    def set_runtime_param(self, key: str, value: Any) -> None:
        """Set a runtime parameter (detected after connection)."""
        self._runtime_params[key] = value

    def get_runtime_param(self, key: str, default: Any = None) -> Any:
        """Get a runtime parameter."""
        return self._runtime_params.get(key, default)

    def get_server_version(self) -> Tuple[int, int, int]:
        """Return the SQLite version this dialect is configured for."""
        return self.version

    def _effective_version(self) -> Tuple[int, int, int]:
        """Resolve the version used for capability checks.

        Returns the explicitly configured or adapted version, falling back to
        the sqlite3 library version, which is always known without adaptation.
        """
        if self._version is not None:
            return self._version
        import sqlite3

        return tuple(sqlite3.sqlite_version_info[:3])

    def create_schema_differ(self):
        """Return the SQLite schema differ (content-based FK matching)."""
        from rhosocial.activerecord.backend.impl.sqlite.schema.differ import (
            SQLiteSchemaDiffer,
        )

        return SQLiteSchemaDiffer()

    # region Protocol Support Checks based on version
    def supports_basic_cte(self) -> bool:
        """Basic CTEs are supported since SQLite 3.8.3."""
        return self._effective_version() >= (3, 8, 3)

    def supports_recursive_cte(self) -> bool:
        """Recursive CTEs are supported since SQLite 3.8.3."""
        return self._effective_version() >= (3, 8, 3)

    def supports_materialized_cte(self) -> bool:
        """MATERIALIZED hint is supported since SQLite 3.35.0."""
        return self._effective_version() >= (3, 35, 0)

    def supports_returning_insert(self) -> bool:
        """RETURNING clause is supported for INSERT since SQLite 3.35.0."""
        return self.version >= (3, 35, 0)

    def supports_returning_update(self) -> bool:
        """RETURNING clause is supported for UPDATE since SQLite 3.35.0."""
        return self.version >= (3, 35, 0)

    def supports_returning_delete(self) -> bool:
        """RETURNING clause is supported for DELETE since SQLite 3.35.0."""
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

    def supports_json_arrow_operators(self) -> bool:
        """SQLite supports -> and ->> operators from version 3.38.0+."""
        return self.version >= (3, 38, 0)

    def get_json_access_operator(self) -> str:
        """SQLite uses '->' for JSON access."""
        return "->"

    def supports_json_table(self) -> bool:
        """SQLite does not directly support JSON_TABLE as a table function."""
        return False

    # endregion

    # region Custom Implementations for SQLite-specific behavior
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
        if options is not None and hasattr(options, "type") and options.type == ExplainType.QUERY_PLAN:
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

    def supports_on_conflict_clause(self) -> bool:
        """Whether the ON CONFLICT clause form is supported in INSERT."""
        return True

    def supports_multiple_on_conflict_clauses(self) -> bool:
        """Whether multiple ON CONFLICT clauses are supported in a single INSERT.

        Multiple ON CONFLICT clauses are supported since SQLite 3.35.0.
        """
        return self.version >= (3, 35, 0)

    def supports_lateral_join(self) -> bool:
        """Whether LATERAL joins are supported."""
        # LATERAL joins are supported in SQLite
        return True

    def supports_ordered_set_aggregation(self) -> bool:
        """Whether ordered-set aggregate functions are supported."""
        return False

    def supports_truncate(self) -> bool:
        """SQLite does not support TRUNCATE TABLE (use DELETE FROM instead)."""
        return False

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """SQLite does not support TRUNCATE TABLE."""
        raise UnsupportedFeatureError(self.name, "TRUNCATE TABLE", "Use DELETE FROM instead.")

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

    def supports_drop_table_cascade(self) -> bool:
        """SQLite does not recognize the CASCADE keyword on DROP TABLE.

        SQLite has no notion of dependent-object cascading on DROP TABLE;
        ``DROP TABLE t CASCADE`` is a syntax error. Foreign-key behavior is
        governed separately by ``PRAGMA foreign_keys``.
        """
        return False

    def supports_drop_table_restrict(self) -> bool:
        """SQLite does not recognize the RESTRICT keyword on DROP TABLE."""
        return False

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
        """Whether MySQL-style ``CREATE FULLTEXT INDEX`` DDL is supported.

        SQLite uses ``FTS5`` virtual tables for full-text indexing
        instead of a dedicated ``CREATE FULLTEXT INDEX`` statement,
        so this returns ``False``.
        """
        return False

    def supports_fulltext_search(self) -> bool:
        """Whether full-text search querying is supported.

        SQLite provides full-text search through ``FTS5`` virtual tables
        with ``MATCH`` syntax (e.g. ``SELECT ... FROM fts_table WHERE
        fts_table MATCH 'search term'``).  Although the DDL mechanism
        differs from MySQL-style ``CREATE FULLTEXT INDEX``, the query-side
        capability is fully present.
        """
        return True

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

    # endregion

    # endregion


# endregion
