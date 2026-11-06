# src/rhosocial/activerecord/backend/impl/sqlite/mixins/introspection.py
"""
SQLite-specific Introspection implementation.

This module provides the SQLiteIntrospectionCapabilityMixin class.
"""

import re
import sqlite3
from functools import lru_cache
from typing import List, Optional, Tuple, TYPE_CHECKING

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.introspection.types import ProfileSource

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.expression.introspection import (
        ColumnDataProfileQueryStatement,
        ColumnInfoQueryStatement,
        ColumnValueSampleQueryStatement,
        DatabaseInfoQueryStatement,
        ForeignKeyQueryStatement,
        IndexInfoQueryStatement,
        JoinCoverageQueryStatement,
        TableInfoQueryStatement,
        TableListQueryStatement,
        TriggerInfoQueryStatement,
        TriggerListQueryStatement,
        ViewInfoQueryStatement,
        ViewListQueryStatement,
    )
    from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
        SQLiteIndexDdlStatement,
        SQLiteIndexOwnerStatement,
        SQLitePragmaQueryStatement,
        SQLitePragmaSetStatement,
        SQLiteTableCountStatement,
        SQLiteTableDdlStatement,
        SQLiteTableStorageStatement,
    )
    from rhosocial.activerecord.backend.introspection.types import IntrospectionScope


#: A PRAGMA value the engine reads in its own vocabulary rather than as a SQL
#: literal: keywords (``WAL``, ``ON``) and numbers (``1000``). Anything else is
#: written as an escaped string literal, which is the form that cannot carry
#: statement text into the assignment.
_PRAGMA_VALUE_TOKEN = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_+\-.]*")


@lru_cache(maxsize=1)
def _dbstat_compiled_in() -> bool:
    """Whether the linked SQLite library was built with the ``dbstat`` table.

    ``PRAGMA compile_options`` names ``ENABLE_DBSTAT_VTAB`` when it was, and
    the library is the same one every connection in this process opens -- so a
    throwaway in-memory connection answers for all of them. The answer is
    cached because a compile-time fact does not change under a running
    process, and answering it raises no exception outward: a build that cannot
    answer is a build without the table, which is what ``False`` says.
    """
    try:
        connection = sqlite3.connect(":memory:")
    except sqlite3.Error:  # pragma: no cover - a library that cannot open
        return False
    try:
        options = connection.execute("PRAGMA compile_options").fetchall()
        return any("ENABLE_DBSTAT_VTAB" in str(row[0]) for row in options)
    except sqlite3.Error:  # pragma: no cover - a pragma that cannot answer
        return False
    finally:
        connection.close()


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
        return self.version_at_least((3, 6, 19))

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
        """SQLite keeps no per-index use counter, so it cannot report one.

        Not "SQLite has no indexes" -- ``PRAGMA index_list`` answers those. It
        has no statistic to derive "never served a query" from: the query
        planner does not maintain per-index counters, and ``sqlite_stat1`` is
        a table-size estimator, not a use record. Answering ``True`` here would
        promise a number that does not exist.
        """
        return False

    # ========== Structure Information ==========

    def supports_partition_info(self) -> bool:
        """SQLite does not support partition information (no partitions in SQLite)."""
        return False

    def supports_object_dependencies(self) -> bool:
        """SQLite does not support object dependencies introspection."""
        return False

    def supports_extensions(self) -> bool:
        """SQLite has registered virtual table modules (``PRAGMA module_list``) but does not expose them.

        It used to answer ``True`` on the strength of that pragma alone, with
        no query formatting, no result type and no CLI type behind it -- a
        caller was promised an answer it could not get, which is worse than
        ``False``. ``False`` until the listing exists; when it does, the
        engine's own name for it (``supports_module_introspection``) is the
        honest one, because "module" and PostgreSQL's "extension" are not the
        same thing and this dialect should not be read as claiming they are.
        """
        return False

    def supports_table_storage_introspection(self) -> bool:
        """Whether per-table storage metrics introspection is supported.

        The answer is the ``dbstat`` virtual table, which is a compile-time
        option (``SQLITE_ENABLE_DBSTAT_VTAB``) rather than a version: a build
        without it has no page-level facts to report, and the honest answer
        is False rather than a storage list of zeroes.
        """
        return _dbstat_compiled_in()

    # ========== DDL Extraction ==========

    def supports_ddl_extraction(self) -> bool:
        """SQLite cannot yet read back the DDL of an object.

        ``sqlite_master`` does keep the statement text each object was declared
        with, so the raw material is there -- but there is no
        ``format_ddl_statement_query_statement`` behind this probe, so a
        ``True`` here promised an answer that resolved to the protocol stub
        and raised ``ProtocolNotImplementedError`` at the caller. A probe
        answered ``True`` with nothing behind it is worse than a ``False``: the
        caller believes it asked a question and got a refusal instead of an
        answer.

        ``False`` until a formatter exists. Unlike PostgreSQL and MySQL, which
        assemble a faithful ``CREATE TABLE`` from the catalogue and mark the
        assembly ``native=False``, SQLite has no such assembly written -- and
        inventing one that cannot reproduce storage constraints, virtual-table
        options or a trigger body would read as authoritative when it is not.
        """
        return False

    def supports_column_data_profile(self) -> bool:
        """SQLite answers a column data profile by aggregating the rows.

        There is no statistics catalogue to read: ``sqlite_stat1`` is a
        table-size estimator, not a per-column profile. So the answer is exact
        and paid for in time, which is why the result must be labelled
        ``AGGREGATE`` rather than left to look like an estimate.
        """
        return True

    def supports_column_value_sample(self) -> bool:
        """SQLite answers a value listing by aggregating with a limit.

        Nothing is precomputed, so this costs a grouped scan -- the same order
        as the profile itself, which is why the two are separate probes rather
        than one call that would force the cheap half to pay for the dear one.
        """
        return True

    def supports_join_coverage(self) -> bool:
        """SQLite answers overlap by counting distinct values on both sides.

        Exact, and paid for with two scans plus an intersection. Answering
        ``True`` is right because the probe asks whether the engine *can*
        answer, not whether it can answer cheaply -- the cost belongs in the
        docstring, not in a False that would claim SQLite cannot measure its
        own rows.
        """
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
        return self.version_at_least((3, 37, 0))

    def supports_table_xinfo_pragma(self) -> bool:
        """PRAGMA table_xinfo (includes hidden columns) requires SQLite 3.26.0+.

        Returns:
            True if PRAGMA table_xinfo is available.
            If False, use PRAGMA table_info instead.
        """
        return self.version_at_least((3, 26, 0))

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

    def format_table_storage_statement(
        self, expr: "SQLiteTableStorageStatement"
    ) -> Tuple[str, tuple]:
        """Format the per-page storage question the ``dbstat`` table answers.

        The rows come back one per page -- ``name`` naming the btree and
        ``pgsize`` its size -- because the reduction to one byte count per
        btree belongs to the parser, which attributes index pages to their
        owning table in the same pass. No ``WHERE`` and no aggregation are
        asked of the engine: the question is "what exists", and the answer's
        meaning is decided in Python.

        Raises:
            UnsupportedFeatureError: If this SQLite build has no ``dbstat``.
        """
        if not self.supports_table_storage_introspection():
            raise UnsupportedFeatureError(self.name, "table storage introspection")

        from rhosocial.activerecord.backend.expression import Column, QueryStatement
        from rhosocial.activerecord.backend.expression.sources.relation import (
            NamedRelationRef,
        )
        from ..expression import SQLiteTable

        return QueryStatement(
            self,
            select=[Column(self, "name"), Column(self, "pgsize")],
            from_=NamedRelationRef(
                self,
                SQLiteTable(
                    self,
                    "dbstat",
                    schema_name=expr.schema or "main",
                    schema_need_quote=False,
                    name_need_quote=False,
                ),
            ),
        ).to_sql()

    def format_index_owner_statement(self, expr: "SQLiteIndexOwnerStatement") -> Tuple[str, tuple]:
        """Format the question that attributes each index to its table.

        ``sqlite_master`` is read once for the whole database: the mapping is
        a catalogue fact, and the storage reducer needs every entry rather
        than one table's, so the per-table PRAGMA would ask the same question
        once per table.

        Args:
            expr: The index-ownership question.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            ComparisonPredicate,
            Literal,
        )

        return self.sqlite_master_query(
            expr.schema or "main",
            [Column(self, "name"), Column(self, "tbl_name")],
            [
                ComparisonPredicate(
                    self, "eq", Column(self, "type"), Literal(self, "index", inline=True)
                ),
            ],
            [Column(self, "name")],
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

    # ========== Data Profiles (row-shaped answers) ==========

    def _user_relation(self, table_name: str, schema: "Optional[str]", alias: "Optional[str]" = None):
        """A user table as a FROM source, quoted by this dialect.

        The opposite of :meth:`sqlite_master_query`'s catalogue relation: a
        user table is whatever its owner declared -- mixed case, a space, a
        reserved word -- so its name and its database are left to the
        dialect's identifier renderer. The database is the attached name
        SQLite calls a schema, which is why it rides on
        :class:`~...expression.table.SQLiteTable` rather than being spelled
        here. The alias is optional, and is what tells the two sides of a
        coverage measurement apart.
        """
        from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
        from ..expression import SQLiteTable

        return NamedRelationRef(
            self, SQLiteTable(self, table_name, schema_name=schema), alias=alias
        )

    def _profile_label(self, text: "Optional[str]", alias: str):
        """A constant label as a named select-list entry.

        ``Literal`` is deliberately unaliasable -- a value has nothing to name
        (see :class:`~...expression.core.Literal`) -- so the constant is cast
        to text, which is the smallest node in the tree that produces a named
        result. The cast is not there for its type: it is there so the label
        can be called ``column_name`` or ``source``, which is what the parser
        reads. ``None`` is the same node carrying SQL NULL, which is how the
        empty profile says "the column name is absent" without inventing one.
        """
        from rhosocial.activerecord.backend.expression.core import (
            CastExpression,
            Literal,
        )
        from rhosocial.activerecord.backend.expression.types.string import CharType

        return CastExpression(self, Literal(self, text, inline=True), CharType(self), alias=alias)

    def _profile_arm(self, table_name: str, schema: "Optional[str]", column_name: str):
        """One column's arm of the profile, as a node.

        The seven entries are the family's contract: the column's own name,
        the null count, the distinct count, the two endpoints, the row count
        the parser divides by, and the provenance. The null count is a ``SUM``
        over a ``CASE`` so an empty table answers NULL rather than a
        fabricated zero; the distinct count is ``COUNT(DISTINCT ...)``; the
        endpoints are the engine's own ``MIN``/``MAX``; and ``COUNT(*)`` rides
        the same scan, so an arm reads its table once.

        ``COUNT(*)`` and the null count share a scan because they are two
        halves of one fraction: the parser divides one by the other, and
        reading the same table twice to get them would double the cost of the
        cheapest part of the answer.
        """
        from rhosocial.activerecord.backend.expression import (
            CaseExpression,
            Column,
            CountFunction,
            FunctionCall,
            IsNullPredicate,
            Literal,
            QueryStatement,
            RowCountWildcard,
            SumFunction,
        )

        column = Column(self, column_name)
        return QueryStatement(
            self,
            select=[
                self._profile_label(column_name, "column_name"),
                SumFunction(
                    self,
                    CaseExpression(
                        self,
                        cases=[
                            (
                                IsNullPredicate(self, column),
                                Literal(self, 1, inline=True),
                            )
                        ],
                        else_result=Literal(self, 0, inline=True),
                    ),
                ).as_("null_count"),
                CountFunction(self, column, distinct=True).as_("distinct_count"),
                FunctionCall(self, "MIN", column).as_("min_value"),
                FunctionCall(self, "MAX", column).as_("max_value"),
                CountFunction(self, RowCountWildcard(self)).as_("row_count"),
                # The provenance travels in the data, not in a docstring: a
                # consumer comparing a SQLite profile with a PostgreSQL one
                # must be able to tell an exact count from a sampled estimate
                # without knowing which engine it asked. The word is the enum
                # member's own spelling, so the closed set has one source.
                self._profile_label(ProfileSource.AGGREGATE.value, "source"),
            ],
            from_=self._user_relation(table_name, schema),
        )

    def format_column_data_profile_query_statement(
        self, expr: "ColumnDataProfileQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a per-column profile by aggregating the rows themselves.

        SQLite has no statistics catalogue to read, so the answer is exact
        and paid for in time -- which is why the result must be labelled
        ``AGGREGATE`` rather than left to look like an estimate. That labelling
        is the caller's, from ``source``.

        One ``UNION ALL`` arm per column, over the column list the expression
        carries: SQL cannot pivot ``SUM(col IS NULL)`` across columns it was
        never told about, so an aggregating dialect genuinely needs that list
        where a catalogue-based one does not.

        ``null_count`` rather than a fraction: dividing by a row count that
        may legitimately be zero belongs in the parser, not in a SQL expression
        that would then have to guard against it.

        An empty column list answers with no rows. That case cannot arise from
        a real table -- SQLite requires at least one column -- but the branch
        has to render, so it is a statement that selects no rows rather than a
        special-case string.
        """
        params = expr.get_params()
        table_name = params.get("table_name")
        schema = params.get("schema")

        arms = [self._profile_arm(table_name, schema, name) for name in expr.columns]
        if not arms:
            # No arm to join: a projection of NULL with a predicate that
            # cannot hold, which is what "no columns" answers as.
            from rhosocial.activerecord.backend.expression import (
                ComparisonPredicate,
                Literal,
                QueryStatement,
                WhereClause,
            )

            return QueryStatement(
                self,
                select=[self._profile_label(None, "column_name")],
                where=WhereClause(
                    self,
                    ComparisonPredicate(
                        self,
                        "eq",
                        Literal(self, 0, inline=True),
                        Literal(self, 1, inline=True),
                    ),
                ),
            ).to_sql()

        # Every arm is a real QueryStatement, so the compound question is one
        # node rather than a join of rendered text: the operator word is the
        # dialect's, and the projection, identifiers and parameters of each
        # arm stay with the renderer that owns them.
        from rhosocial.activerecord.backend.expression.query_sources import (
            SetOperationKind,
        )
        from rhosocial.activerecord.backend.expression.statements import (
            SetOperationStatement,
        )

        return SetOperationStatement(
            self, op=SetOperationKind.UNION_ALL, parts=arms
        ).to_sql()

    def format_column_value_sample_query_statement(
        self, expr: "ColumnValueSampleQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a most-frequent-values listing with a grouped scan.

        Nothing is precomputed in SQLite, so this costs a ``GROUP BY`` over the
        column plus a sort of the groups -- the same order as the profile
        itself, which is why the two are separate probes rather than one call
        that would make the cheap half pay for the dear one.

        ``ORDER BY COUNT(*) DESC`` is what makes the answer "the most frequent
        values" rather than "the first values"; ties break by the value so two
        runs of the same query agree. The ``LIMIT`` is a bind parameter, as it
        is everywhere else in this dialect: keeping it bound means the
        caller's integer is never spliced into statement text, and SQLite
        accepts the placeholder once it reaches it as a number.
        """
        from rhosocial.activerecord.backend.expression import (
            Column,
            CountFunction,
            GroupByHavingClause,
            LimitOffsetClause,
            OrderByClause,
            QueryStatement,
            RowCountWildcard,
        )

        column = Column(self, expr.column_name)
        return QueryStatement(
            self,
            select=[
                column.as_("value"),
                CountFunction(self, RowCountWildcard(self)).as_("count"),
            ],
            from_=self._user_relation(expr.table_name, expr.schema),
            group_by_having=GroupByHavingClause(
                self, group_by=[Column(self, expr.column_name)]
            ),
            order_by=OrderByClause(
                self,
                expressions=[
                    (CountFunction(self, RowCountWildcard(self)), "DESC"),
                    (Column(self, expr.column_name), "ASC"),
                ],
            ),
            limit_offset=LimitOffsetClause(self, limit=int(expr.limit)),
        ).to_sql()

    def _coverage_fraction(self, column, source, other_column, other_source):
        """One side of the overlap: the share of *column* the other side holds.

        The numerator counts the *distinct* values of *column* that also occur
        in *other_column*, as a ``COUNT(*)`` over a derived table of those
        distinct values; the denominator counts *column*'s distinct non-NULL
        values. Distinct on both sides is what makes the figure a coverage of
        values rather than of rows -- a key repeated a thousand times that
        matches once would otherwise read as well covered.

        ``IS NOT NULL`` is written on both halves rather than relied upon. In
        the numerator it is load-bearing: ``SELECT DISTINCT`` treats a NULL as
        one value, so counting it would credit the tested side with a match it
        does not have. In the divisor ``COUNT(DISTINCT ...)`` skips NULLs on
        its own, but the statement says so explicitly, because the share is of
        the values that could join and that is the fact being measured.
        ``NULLIF(..., 0)`` then makes a column with no value at all answer
        NULL rather than 0, which the parser reads as "no measurement": the
        difference between "nothing matched" and "nothing to match" survives
        to the caller.

        ``* 1.0`` is load-bearing on this engine, unlike MySQL's version of
        this method: SQLite divides integers by truncation, so
        ``COUNT(*) / COUNT(...)`` would answer 0 for every share below one.
        """
        from rhosocial.activerecord.backend.expression import (
            CountFunction,
            FunctionCall,
            InPredicate,
            Literal,
            LogicalPredicate,
            QueryStatement,
            RowCountWildcard,
            SelectModifier,
            Subquery,
            WhereClause,
        )
        from rhosocial.activerecord.backend.expression.sources import DerivedTableSource

        overlap = QueryStatement(
            self,
            select=[column],
            from_=source,
            where=WhereClause(
                self,
                LogicalPredicate(
                    self,
                    "AND",
                    column.is_not_null(),
                    InPredicate(
                        self,
                        column,
                        Subquery(
                            self,
                            QueryStatement(
                                self,
                                select=[other_column],
                                from_=other_source,
                                where=WhereClause(self, other_column.is_not_null()),
                            ),
                        ),
                    ),
                ),
            ),
            select_modifier=SelectModifier.DISTINCT,
        )
        covered = Subquery(
            self,
            QueryStatement(
                self,
                select=[CountFunction(self, RowCountWildcard(self))],
                from_=DerivedTableSource(self, overlap, alias="covered"),
            ),
        )
        total = Subquery(
            self,
            QueryStatement(
                self,
                select=[
                    FunctionCall(
                        self,
                        "NULLIF",
                        CountFunction(self, column, distinct=True),
                        Literal(self, 0, inline=True),
                    )
                ],
                from_=source,
                where=WhereClause(self, column.is_not_null()),
            ),
        )
        return (covered * Literal(self, 1.0, inline=True)) / total

    def format_join_coverage_query_statement(
        self, expr: "JoinCoverageQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a two-sided coverage measurement over distinct values.

        Both sides are counted as *distinct values*, not rows: a heavily
        repeated key that matches once would otherwise look well covered.

        NULLs are excluded from both numerators and denominators, because a
        NULL is not a value that could ever join -- counting it would drag
        coverage down for a reason that has nothing to do with the join.

        Two subqueries in one row rather than two round trips: the two
        fractions are only meaningful together.

        The aliases ``l`` and ``r`` are what keep the two columns apart in the
        rendered statement, and they are quoted like every other identifier.
        """
        from rhosocial.activerecord.backend.expression import Column, QueryStatement

        params = expr.get_params()
        schema = params.get("schema")

        left_source = self._user_relation(params.get("left_table"), schema, alias="l")
        right_source = self._user_relation(params.get("right_table"), schema, alias="r")
        left_column = Column(self, params.get("left_column"), table="l")
        right_column = Column(self, params.get("right_column"), table="r")

        return QueryStatement(
            self,
            select=[
                self._coverage_fraction(
                    left_column, left_source, right_column, right_source
                ).as_("left_coverage"),
                self._coverage_fraction(
                    right_column, right_source, left_column, left_source
                ).as_("right_coverage"),
            ],
        ).to_sql()