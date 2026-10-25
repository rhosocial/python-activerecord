# src/rhosocial/activerecord/backend/impl/sqlite/mixins/introspection.py
"""
SQLite-specific Introspection implementation.

This module provides the SQLiteIntrospectionCapabilityMixin class.
"""

import re
from typing import List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.introspection import (
        DatabaseInfoQueryStatement,
        TableListQueryStatement,
        TableInfoQueryStatement,
        ColumnInfoQueryStatement,
        IndexInfoQueryStatement,
        ForeignKeyQueryStatement,
        ViewListQueryStatement,
        ViewInfoQueryStatement,
        TriggerListQueryStatement,
        TriggerInfoQueryStatement,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
        SQLiteIndexDdlStatement,
        SQLitePragmaQueryStatement,
        SQLitePragmaSetStatement,
        SQLiteTableCountStatement,
        SQLiteTableDdlStatement,
    )
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


#: A PRAGMA value the engine reads in its own vocabulary rather than as a SQL
#: literal: keywords (``WAL``, ``ON``) and numbers (``1000``). Anything else is
#: written as an escaped string literal, which is the form that cannot carry
#: statement text into the assignment.
_PRAGMA_VALUE_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_+\-.]*")


class SQLiteIntrospectionCapabilityMixin:
    """SQLite introspection capability declaration.

    This mixin implements the IntrospectionSupport protocol by declaring
    which introspection features SQLite supports based on version.
    The actual introspection implementation is in the backend layer
    via SQLiteIntrospectionMixin from the introspection module.

    Dialects only declare capabilities (supports_* methods), they do not
    implement the actual introspection methods.

    Version requirements for SQLite introspection features:
    - PRAGMA table_list: SQLite 3.37.0+ (fallback to sqlite_master query)
    - PRAGMA table_xinfo: SQLite 3.26.0+ (includes hidden columns)
    - PRAGMA table_info: All versions
    - PRAGMA index_list/index_info: All versions
    - PRAGMA foreign_key_list: SQLite 3.6.19+
    """

    # ========== Capability Detection ==========

    def supports_introspection(self) -> bool:
        """SQLite supports introspection."""
        return True

    def supports_database_info(self) -> bool:
        """SQLite supports database info."""
        return True

    def supports_table_introspection(self) -> bool:
        """SQLite supports table introspection."""
        return True

    def supports_column_introspection(self) -> bool:
        """SQLite supports column introspection.

        PRAGMA table_info is available in all versions.
        PRAGMA table_xinfo (with hidden column support) needs 3.26.0+.
        """
        return True

    def supports_index_introspection(self) -> bool:
        """SQLite supports index introspection."""
        return True

    def supports_foreign_key_introspection(self) -> bool:
        """SQLite supports foreign key introspection.

        PRAGMA foreign_key_list was added in SQLite 3.6.19 (2009-10-14).
        Note: Foreign key constraints are disabled by default and must be
        enabled via 'PRAGMA foreign_keys = ON'.
        """
        version = self.version
        return version >= (3, 6, 19)

    def supports_view_introspection(self) -> bool:
        """SQLite supports view introspection."""
        return True

    def supports_trigger_introspection(self) -> bool:
        """SQLite supports trigger introspection."""
        return True

    # ========== Runtime Statistics ==========

    def supports_runtime_stats(self) -> bool:
        """SQLite does not support runtime statistics introspection."""
        return False

    def supports_table_stats(self) -> bool:
        """SQLite does not support table statistics introspection."""
        return False

    def supports_index_stats(self) -> bool:
        """SQLite does not support index statistics introspection."""
        return False

    def supports_unused_indexes_detection(self) -> bool:
        """SQLite does not support unused indexes detection."""
        return False

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """SQLite does not support partition information (no partitions in SQLite)."""
        return False

    def supports_object_dependencies(self) -> bool:
        """SQLite does not support object dependencies introspection."""
        return False

    def supports_extensions(self) -> bool:
        """SQLite supports extension introspection via pragma_module_list."""
        return True

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """SQLite supports DDL extraction via sqlite_master."""
        return True

    def supports_ddl_extraction_native(self) -> bool:
        """SQLite does not have native DDL extraction (requires assembly)."""
        return False

    # ========== Fine-grained Capability Detection ==========

    def supports_table_list_pragma(self) -> bool:
        """PRAGMA table_list requires SQLite 3.37.0+.

        Returns:
            True if PRAGMA table_list is available.
            If False, fallback to sqlite_master query.
        """
        return self.version >= (3, 37, 0)

    def supports_table_xinfo_pragma(self) -> bool:
        """PRAGMA table_xinfo (includes hidden columns) requires SQLite 3.26.0+.

        Returns:
            True if PRAGMA table_xinfo is available.
            If False, use PRAGMA table_info instead.
        """
        return self.version >= (3, 26, 0)

    def get_supported_introspection_scopes(self) -> List["IntrospectionScope"]:
        """Get list of supported introspection scopes."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        scopes = [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]
        # Foreign key introspection requires SQLite 3.6.19+
        if self.supports_foreign_key_introspection():
            scopes.append(IntrospectionScope.FOREIGN_KEY)
        return scopes

    # ========== Query Formatting ==========

    # ------------------------------------------------------------------
    # The sqlite_master READ, expressed once
    # ------------------------------------------------------------------
    def sqlite_master_query(
        self,
        schema: "str",
        projections: "list",
        conditions: "list",
        order_by: "Optional[list]" = None,
    ) -> Tuple[str, tuple]:
        """Build a SELECT over ``sqlite_master`` as an expression tree.

        Every introspection query that reads ``sqlite_master`` is this shape --
        a projection, a conjunction of conditions, and an optional ordering --
        so the shape lives here and each formatter supplies only what varies.
        What a query *asks* is then a structure the rest of the framework can
        inspect, instead of a string reassembled one clause at a time.

        The relation is qualified by *schema*, which on this backend is the name
        of the database being read -- ``main`` by default, or an
        ``ATTACH``-ed database. Dropping the qualifier is not neutral: it would
        silently read the primary database when a caller asked for another one,
        returning rows from the wrong database instead of either working or
        failing. :class:`~...expression.table.SQLiteTable` carries the name, and
        this dialect names it because SQLite's schema is that database name
        rather than the SQL-standard construct.

        Args:
            schema: The database whose ``sqlite_master`` is read.
            projections: The select list, in order.
            conditions: Conditions to AND together.
            order_by: The ordering expressions, or ``None`` for no ORDER BY.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.sources.relation import (
            NamedRelationRef,
        )
        from ..expression import SQLiteTable

        kwargs: "dict" = {
            "select": projections,
            "from_": NamedRelationRef(
                self,
                SQLiteTable(
                    self,
                    "sqlite_master",
                    schema_name=schema,
                    schema_need_quote=False,
                    name_need_quote=False,
                ),
            ),
            "where": WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
        }
        if order_by is not None:
            kwargs["order_by"] = OrderByClause(self, order_by)
        return QueryStatement(self, **kwargs).to_sql()

    def format_database_info_query_statement(self, expr: "DatabaseInfoQueryStatement") -> Tuple[str, tuple]:
        """Format database information query.

        SQLite doesn't have a specific query for database info, so we use
        sqlite_version() and count tables in sqlite_master.

        Args:
            expr: Database info expression with parameters.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import FunctionCall, QueryStatement

        # No FROM: this query reads no table, it asks the engine a question.
        return QueryStatement(
            self,
            select=[FunctionCall(self, "sqlite_version", alias="version")],
        ).to_sql()

    def format_pragma_query_statement(self, expr: "SQLitePragmaQueryStatement") -> Tuple[str, tuple]:
        """Format a PRAGMA read.

        PRAGMA takes no bind parameters, so the parameters tuple is empty and
        the argument, when the pragma has one, is placed as it was given. The
        statement class does not quote it: the caller that supplies a table or
        index name spells it the way the rest of the dialect spells
        identifiers, and a second quoting pass would change it.

        Args:
            expr: The PRAGMA question.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        name = f"{expr.schema}.{expr.name}" if expr.schema else expr.name
        if expr.argument is None:
            return (f"PRAGMA {name}", ())
        return (f"PRAGMA {name}({expr.argument})", ())

    def format_pragma_set_statement(self, expr: "SQLitePragmaSetStatement") -> Tuple[str, tuple]:
        """Format a PRAGMA assignment.

        The value is statement text, not a bind parameter. A bare keyword or
        number keeps its own spelling (``WAL``, ``1000``); everything else is
        written as an escaped string literal, so a value can never close the
        statement it appears in.

        Args:
            expr: The PRAGMA assignment.

        Returns:
            Tuple of (SQL string, empty parameters tuple).
        """
        name = f"{expr.schema}.{expr.name}" if expr.schema else expr.name
        if expr.argument is not None:
            name = f"{name}({expr.argument})"

        if isinstance(expr.value, str) and _PRAGMA_VALUE_TOKEN.fullmatch(expr.value):
            value = expr.value
        else:
            value = self.format_literal(expr.value)

        return (f"PRAGMA {name} = {value}", ())

    def format_table_count_statement(self, expr: "SQLiteTableCountStatement") -> Tuple[str, tuple]:
        """Count the tables of one database, system tables excluded.

        ``sqlite_master`` names its kind in ``type`` and hides the engine's own
        tables behind the ``sqlite_`` prefix, so both facts are conditions on
        the same read rather than a filter applied to a listing afterwards.

        Args:
            expr: The count question.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            LikeOperator,
            LikePredicate,
            Literal,
            count,
        )

        return self.sqlite_master_query(
            expr.schema or "main",
            [count(self, "*", alias="table_count")],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "type"), Literal(self, "table", inline=True)
                ),
                LikePredicate(
                    self,
                    LikeOperator.NOT_LIKE,
                    Column(self, "name"),
                    Literal(self, "sqlite_%", inline=True),
                ),
            ],
        )

    def format_table_ddl_statement(self, expr: "SQLiteTableDdlStatement") -> Tuple[str, tuple]:
        """Read back the statement a table was declared with.

        ``name`` and ``tbl_name`` are both matched: an index row carries the
        indexed table in ``tbl_name``, a table row carries its own name in
        both, so requiring both selects the table row alone.

        Args:
            expr: The DDL question.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        return self.sqlite_master_query(
            expr.schema or "main",
            [Column(self, "sql")],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "type"), Literal(self, "table", inline=True)
                ),
                ComparisonPredicate(self, "eq", Column(self, "name"), Literal(self, expr.table_name)),
                ComparisonPredicate(
                    self, "eq", Column(self, "tbl_name"), Literal(self, expr.table_name)
                ),
            ],
        )

    def format_index_ddl_statement(self, expr: "SQLiteIndexDdlStatement") -> Tuple[str, tuple]:
        """Read back the statement an index was declared with.

        Only the index's own row carries the ``WHERE`` clause of a partial
        index, and this is the only place that clause can be read from.

        Args:
            expr: The DDL question.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        return self.sqlite_master_query(
            expr.schema or "main",
            [Column(self, "sql")],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "type"), Literal(self, "index", inline=True)
                ),
                ComparisonPredicate(self, "eq", Column(self, "name"), Literal(self, expr.index_name)),
            ],
        )

    def format_table_list_query_statement(self, expr: "TableListQueryStatement") -> Tuple[str, tuple]:
        """Format table list query.

        For SQLite 3.37.0+, use PRAGMA table_list.
        For older versions, query sqlite_master table.

        Args:
            expr: Table list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        schema = params.get("schema") or "main"
        include_views = params.get("include_views", True)
        include_system = params.get("include_system", False)
        table_type = params.get("table_type")

        # Use PRAGMA table_list only when system tables are requested,
        # since PRAGMA cannot filter them out at the SQL level.
        # For user-only queries, sqlite_master provides native filtering.
        if self.supports_table_list_pragma() and include_system:
            from ..expression.introspection import SQLitePragmaQueryStatement

            return SQLitePragmaQueryStatement(self, "table_list", schema=schema).to_sql()

        # Fallback to sqlite_master query (also used for include_system=False
        # because sqlite_master supports NOT LIKE filtering natively).
        #
        # The intent is carried by a tree rather than concatenated, so what this
        # query asks is a structure the rest of the framework can inspect, and
        # the dialect owns only the spelling. The projection is name before
        # type, the IN list is literal-inline so the parameters stay empty
        # exactly as the concatenated form left them, and the system-table
        # exclusion is a NOT LIKE predicate rather than appended text.
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            InPredicate,
            LikeOperator,
            LikePredicate,
            Literal,
            LogicalPredicate,
            OrderByClause,
            QueryStatement,
            WhereClause,
        )

        values = ("table", "view") if include_views else ("table",)
        conditions = [InPredicate(self, Column(self, "type"), Literal(self, values, inline=True))]

        # Exclude system tables unless requested
        if not include_system:
            conditions.append(
                LikePredicate(
                    self,
                    LikeOperator.NOT_LIKE,
                    Column(self, "name"),
                    Literal(self, "sqlite_%", inline=True),
                )
            )

        # Filter by table type if specified
        if table_type:
            spelled = "table" if table_type == "BASE TABLE" else table_type.lower()
            conditions.append(
                ComparisonPredicate(
                    self, "eq", Column(self, "type"), Literal(self, spelled, inline=True)
                )
            )

        query = QueryStatement(
            self,
            select=[Column(self, "name"), Column(self, "type")],
            from_="sqlite_master",
            where=WhereClause(self, LogicalPredicate(self, "AND", *conditions)),
            order_by=OrderByClause(self, [Column(self, "name")]),
        )
        return query.to_sql()

    def format_table_info_query_statement(self, expr: "TableInfoQueryStatement") -> Tuple[str, tuple]:
        """Format single table information query.

        Query sqlite_master for table details.

        Args:
            expr: Table info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"
        from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal

        return self.sqlite_master_query(
            schema,
            [Column(self, "name"), Column(self, "type"), Column(self, "sql")],
            [ComparisonPredicate(self, "eq", Column(self, "name"), Literal(self, table_name))],
        )

    def format_column_info_query_statement(self, expr: "ColumnInfoQueryStatement") -> Tuple[str, tuple]:
        """Format column information query.

        For SQLite 3.26.0+, can use PRAGMA table_xinfo to include hidden columns.
        Otherwise, use PRAGMA table_info.

        Args:
            expr: Column info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        include_hidden = params.get("include_hidden", False)
        schema = params.get("schema") or "main"

        from ..expression.introspection import SQLitePragmaQueryStatement

        # Use table_xinfo for hidden columns if supported and requested
        pragma = "table_xinfo" if include_hidden and self.supports_table_xinfo_pragma() else "table_info"
        return SQLitePragmaQueryStatement(
            self, pragma, self.format_identifier(table_name), schema=schema
        ).to_sql()

    def format_index_info_query_statement(self, expr: "IndexInfoQueryStatement") -> Tuple[str, tuple]:
        """Format index information query.

        Use PRAGMA index_list to get indexes for a table.

        Args:
            expr: Index info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        from ..expression.introspection import SQLitePragmaQueryStatement

        return SQLitePragmaQueryStatement(
            self, "index_list", self.format_identifier(table_name), schema=schema
        ).to_sql()

    def format_foreign_key_query_statement(self, expr: "ForeignKeyQueryStatement") -> Tuple[str, tuple]:
        """Format foreign key information query.

        Use PRAGMA foreign_key_list to get foreign keys for a table.

        Args:
            expr: Foreign key expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name", "")
        schema = params.get("schema") or "main"

        from ..expression.introspection import SQLitePragmaQueryStatement

        return SQLitePragmaQueryStatement(
            self, "foreign_key_list", self.format_identifier(table_name), schema=schema
        ).to_sql()

    def format_view_list_query_statement(self, expr: "ViewListQueryStatement") -> Tuple[str, tuple]:  # noqa: F821
        """Format view list query.

        Query sqlite_master for views.

        Args:
            expr: View list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        schema = params.get("schema") or "main"
        include_system = params.get("include_system", False)

        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            LikeOperator,
            LikePredicate,
            Literal,
        )

        conditions = [
            ComparisonPredicate(
                self, "eq", Column(self, "type"), Literal(self, "view", inline=True)
            )
        ]
        # Exclude system views unless requested
        if not include_system:
            conditions.append(
                LikePredicate(
                    self,
                    LikeOperator.NOT_LIKE,
                    Column(self, "name"),
                    Literal(self, "sqlite_%", inline=True),
                )
            )

        # ``sql`` is the view's own text and it must be projected: the parser
        # reads it for ``IntrospectionViewInfo.definition``, and a projection
        # without it silently reports every view as having no definition --
        # which is not the same answer as "this view has none".
        return self.sqlite_master_query(
            schema,
            [Column(self, "name"), Column(self, "sql")],
            conditions,
            [Column(self, "name")],
        )

    def format_view_info_query_statement(self, expr: "ViewInfoQueryStatement") -> Tuple[str, tuple]:  # noqa: F821
        """Format single view information query.

        Query sqlite_master for view details.

        Args:
            expr: View info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        view_name = params.get("view_name", "")
        schema = params.get("schema") or "main"

        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        conditions = [
            ComparisonPredicate(
                self, "eq", Column(self, "type"), Literal(self, "view", inline=True)
            ),
            # The name is bound, exactly as the concatenated form bound it.
            ComparisonPredicate(self, "eq", Column(self, "name"), Literal(self, view_name)),
        ]
        return self.sqlite_master_query(
            schema, [Column(self, "name"), Column(self, "sql")], conditions
        )

    def format_trigger_list_query_statement(self, expr: "TriggerListQueryStatement") -> Tuple[str, tuple]:  # noqa: F821
        """Format trigger list query.

        Query sqlite_master for triggers, optionally filtered by table.

        Args:
            expr: Trigger list expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        table_name = params.get("table_name")
        schema = params.get("schema") or "main"

        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        conditions = [
            ComparisonPredicate(
                self, "eq", Column(self, "type"), Literal(self, "trigger", inline=True)
            )
        ]
        # Filtering by table drops the ordering -- an asymmetry worth keeping
        # visible in the tree rather than hiding in a string branch.
        if table_name:
            conditions.append(
                ComparisonPredicate(self, "eq", Column(self, "tbl_name"), Literal(self, table_name))
            )
            return self.sqlite_master_query(
                schema,
                [Column(self, "name"), Column(self, "tbl_name"), Column(self, "sql")],
                conditions,
            )

        return self.sqlite_master_query(
            schema,
            [Column(self, "name"), Column(self, "tbl_name"), Column(self, "sql")],
            conditions,
            [Column(self, "name")],
        )

    def format_trigger_info_query_statement(self, expr: "TriggerInfoQueryStatement") -> Tuple[str, tuple]:  # noqa: F821
        """Format single trigger information query.

        Query sqlite_master for trigger details.

        Args:
            expr: Trigger info expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        params = expr.get_params()
        trigger_name = params.get("trigger_name", "")
        schema = params.get("schema") or "main"

        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        conditions = [
            ComparisonPredicate(
                self, "eq", Column(self, "type"), Literal(self, "trigger", inline=True)
            ),
            ComparisonPredicate(self, "eq", Column(self, "name"), Literal(self, trigger_name)),
        ]
        return self.sqlite_master_query(
            schema,
            [Column(self, "name"), Column(self, "tbl_name"), Column(self, "sql")],
            conditions,
        )

