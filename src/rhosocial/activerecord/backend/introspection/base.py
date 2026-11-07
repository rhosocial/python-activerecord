# src/rhosocial/activerecord/backend/introspection/base.py
"""
Abstract introspector base classes.

This module provides the abstract base classes for database introspection,
following the project's sync/async parity principle:

1. IntrospectorMixin: the shared base every introspector inherits, which
   knows the default schema. It holds no state, does no I/O and never sees
   a result row.

2. AbstractIntrospector: Synchronous introspector with all I/O methods
   being synchronous.

3. AsyncAbstractIntrospector: Asynchronous introspector with all I/O methods
   being async. Method names match the sync version (no _async suffix).

Design principles:
  - Sync and Async are separate and cannot coexist in the same class.
  - I/O methods have identical signatures between sync and async versions,
    differing only in async/await keywords.
  - The cache is a component of its own (see cache.py): the manager owns an
    IntrospectionCache and delegates invalidation to it, because results
    outlive a single call. The in-memory implementation is the default; a
    backend may inject its own.
  - Asking for a statement, running it and parsing the rows are three
    separate jobs: this module keeps the first pure (the ``*_statement``
    factories on the manager), and puts the other two on the manager.
  - No SQL is built here. Each factory picks a statement object; the
    dialect's ``format_*_query_statement`` decides the SQL that object
    renders, so a backend overrides the factory rather than rewriting SQL.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, TYPE_CHECKING

from .cache import InMemoryIntrospectionCache, IntrospectionCache
from .defaults import VALUE_SAMPLE_LIMIT
from .types import (
    IntrospectionDatabaseInfo,
    IntrospectionTableInfo,
    IntrospectionColumnInfo,
    IndexInfo,
    IntrospectionForeignKeyInfo,
    IntrospectionViewInfo,
    IntrospectionTriggerInfo,
    IntrospectionScope,
    ColumnDataProfile,
    ColumnValueFrequency,
    DDLStatement,
    ProfileSource,
    IndexUsageStats,
    JoinCoverage,
    ObjectDependency,
    RuntimeMetricItem,
    TableUsageStats,
    UnusedIndexInfo,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase
    from ..expression.introspection import (
        ColumnDataProfileQueryStatement,
        ColumnInfoQueryStatement,
        ColumnValueSampleQueryStatement,
        DatabaseInfoQueryStatement,
        DDLStatementQueryStatement,
        ForeignKeyQueryStatement,
        IndexInfoQueryStatement,
        IndexUsageStatsQueryStatement,
        JoinCoverageQueryStatement,
        ObjectDependencyQueryStatement,
        RuntimeMetricsQueryStatement,
        TableListQueryStatement,
        TableUsageStatsQueryStatement,
        TriggerListQueryStatement,
        UnusedIndexesQueryStatement,
        ViewInfoQueryStatement,
        ViewListQueryStatement,
    )
    from .executor import IntrospectorExecutor, AsyncIntrospectorExecutor


class IntrospectorMixin:
    """Mixin providing shared non-I/O functionality for introspectors.

    This mixin knows which schema a query means by default and holds
    nothing else: no state, no I/O, and it never sees a result row, which
    is what makes it safe to share between the sync and the async manager
    and between every backend.

    Caching and parsing belong to the manager that inherits this class --
    the cache because results outlive a call, and the parsing contract
    because it is the manager that has a database to answer.
    """

    # ------------------------------------------------------------------ #
    # Dialect shortcut
    # ------------------------------------------------------------------ #

    @property
    def dialect(self) -> "SQLDialectBase":
        """Get the SQL dialect from the backend."""
        return self._backend.dialect

    @property
    def server_version(self) -> Optional[Tuple[int, int, int]]:
        """The server version to report, or ``None`` when nothing knows it.

        Three sources, cheapest and most authoritative first: the adapted
        dialect, the version the dialect names without a handshake (SQLite's
        engine *is* its driver's library), then what the backend cached from
        its last connection. Reading it never raises and never performs I/O.

        Parsers fill ``IntrospectionDatabaseInfo.version`` from this rather
        than from ``dialect.version``: the strict property raises before
        adaptation, and a parser has no business refusing to report a
        database just because the version is not known yet.
        """
        version = self.dialect.version_or_none
        if version is not None:
            return version
        return self._backend.get_cached_server_version()

    @property
    def default_schema(self) -> str:
        """The schema name this database calls its own by default.

        Subclasses override to name the database-specific default (``"main"``
        for SQLite, ``"public"`` for PostgreSQL). Empty by default so generic
        callers still work against a backend that has no such name.
        """
        return ""


class IntrospectorBase(IntrospectorMixin, ABC):
    """What every introspection manager is: owns the cache, provides the
    statement factories, and contracts the parsing of database rows.

    The sync and the async manager differ only in how they run the SQL the
    statements render -- everything below is common to both, so it is
    declared once here rather than twice. That includes the factories: a
    backend overrides ``table_list_statement`` and both managers see it.
    """

    def __init__(self, backend: Any, executor: Any, cache: Optional[IntrospectionCache] = None) -> None:
        self._backend = backend
        self._executor = executor
        #: The only mutable state in this path. A component with a lifetime
        #: of its own rather than borrowed fields, and injectable, so a
        #: backend can put its own implementation here.
        self._cache: IntrospectionCache = (
            cache if cache is not None else InMemoryIntrospectionCache()
        )

    # ------------------------------------------------------------------ #
    # Statement factories
    #
    # One factory per introspection family. Each returns a *statement
    # object* and renders nothing: the dialect's
    # ``format_*_query_statement`` decides the SQL. A backend that needs a
    # different statement (an extra column, another catalog view) overrides
    # the factory and nothing else -- which is why these live on the shared
    # base and not on one side of the sync/async split.
    # ------------------------------------------------------------------ #

    def database_info_statement(self) -> "DatabaseInfoQueryStatement":
        """Return the statement that asks for database information."""
        from ..expression.introspection import DatabaseInfoQueryStatement

        # Databases that identify themselves by schema (MySQL's database
        # name, for one) need the default schema on the statement. Every
        # parameter is collected at construction: a statement is built once,
        # with everything it asks, and never edited afterwards.
        return DatabaseInfoQueryStatement(
            self.dialect, schema=self.default_schema or None
        )

    def table_list_statement(
        self,
        *,
        schema: Optional[str],
        include_system: bool,
        include_views: bool = True,
        table_type: Optional[str] = None,
    ) -> "TableListQueryStatement":
        """Return the statement that lists tables, views and system tables."""
        from ..expression.introspection import TableListQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return TableListQueryStatement(
            self.dialect,
            schema=target_schema,
            include_views=include_views,
            include_system=include_system,
            table_type=table_type,
        )

    def column_info_statement(
        self,
        *,
        table_name: str,
        schema: Optional[str],
        include_hidden: bool = False,
    ) -> "ColumnInfoQueryStatement":
        """Return the statement that asks for a table's columns.

        *include_hidden* asks the engine for the columns a plain listing leaves
        out. What that means is the backend's business: SQLite keeps generated
        columns behind ``PRAGMA table_xinfo`` and PostgreSQL hides system
        columns unless asked. The default is ``False`` because most callers
        want the table as it reads, but a backend whose own column question
        cannot be answered without them says so at its call site rather than
        changing the default for everyone.
        """
        from ..expression.introspection import ColumnInfoQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ColumnInfoQueryStatement(
            self.dialect,
            table_name=table_name,
            schema=target_schema,
            include_hidden=include_hidden,
        )

    def index_info_statement(
        self,
        *,
        table_name: str,
        schema: Optional[str],
    ) -> "IndexInfoQueryStatement":
        """Return the statement that asks for a table's indexes."""
        from ..expression.introspection import IndexInfoQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return IndexInfoQueryStatement(
            self.dialect, table_name=table_name, schema=target_schema
        )

    def foreign_key_statement(
        self,
        *,
        table_name: str,
        schema: Optional[str],
    ) -> "ForeignKeyQueryStatement":
        """Return the statement that asks for a table's foreign keys."""
        from ..expression.introspection import ForeignKeyQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ForeignKeyQueryStatement(
            self.dialect, table_name=table_name, schema=target_schema
        )

    def view_list_statement(
        self,
        *,
        schema: Optional[str],
        include_system: bool,
    ) -> "ViewListQueryStatement":
        """Return the statement that lists views."""
        from ..expression.introspection import ViewListQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ViewListQueryStatement(
            self.dialect, schema=target_schema, include_system=include_system
        )

    def view_info_statement(
        self,
        *,
        view_name: str,
        schema: Optional[str],
    ) -> "ViewInfoQueryStatement":
        """Return the statement that asks for one view's information."""
        from ..expression.introspection import ViewInfoQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ViewInfoQueryStatement(
            self.dialect, view_name=view_name, schema=target_schema
        )

    def trigger_list_statement(
        self,
        *,
        schema: Optional[str],
        table_name: Optional[str] = None,
    ) -> "TriggerListQueryStatement":
        """Return the statement that lists triggers, optionally one table's."""
        from ..expression.introspection import TriggerListQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return TriggerListQueryStatement(
            self.dialect, schema=target_schema, table_name=table_name
        )

    def unused_indexes_statement(
        self, *, schema: Optional[str]
    ) -> "UnusedIndexesQueryStatement":
        """Return the statement that lists indexes the engine reports as unused.

        An unused index is a fact about the whole database rather than about
        one table, so unlike the trigger statement this takes no table name:
        narrowing the answer is the caller's job, and a dialect asked to
        filter by table would have to invent a filter its statistics cannot
        honour.
        """
        from ..expression.introspection import UnusedIndexesQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return UnusedIndexesQueryStatement(self.dialect, schema=target_schema)

    def table_usage_stats_statement(
        self, *, schema: Optional[str]
    ) -> "TableUsageStatsQueryStatement":
        """Return the statement that reads every table's usage counters.

        One query for the whole schema, because statistics collectors price
        their first query far above their next and the counters are the
        answer: a per-table form would invite looping the catalogue one table
        at a time.
        """
        from ..expression.introspection import TableUsageStatsQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return TableUsageStatsQueryStatement(self.dialect, schema=target_schema)

    def runtime_metrics_statement(
        self, *, schema: Optional[str]
    ) -> "RuntimeMetricsQueryStatement":
        """Return the statement that reads the engine's live measurements.

        No table name, for the reason the class records: runtime facts describe
        the server, so a filter that does not apply to them is worse than no
        filter.
        """
        from ..expression.introspection import RuntimeMetricsQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return RuntimeMetricsQueryStatement(self.dialect, schema=target_schema)

    def index_usage_stats_statement(
        self, *, schema: Optional[str]
    ) -> "IndexUsageStatsQueryStatement":
        """Return the statement that reads per-index use counters.

        One query for the schema, because use counters are cheap to ask for
        all at once and the shape of "is this index worth its space" is a
        question about the set of them.
        """
        from ..expression.introspection import IndexUsageStatsQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return IndexUsageStatsQueryStatement(self.dialect, schema=target_schema)

    def object_dependency_statement(
        self, *, schema: Optional[str], object_name: Optional[str] = None
    ) -> "ObjectDependencyQueryStatement":
        """Return the statement that reads the dependency graph.

        Narrows to one object when the caller names it, which is the "what
        breaks if I drop this" question and the reason the parameter exists;
        omitted, the answer is the whole graph.
        """
        from ..expression.introspection import ObjectDependencyQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ObjectDependencyQueryStatement(
            self.dialect, schema=target_schema, object_name=object_name
        )

    def ddl_statement_statement(
        self,
        *,
        schema: Optional[str],
        object_name: str,
        object_type: Optional[str] = None,
    ) -> "DDLStatementQueryStatement":
        """Return the statement that reads one object's DDL.

        Always about one object: a DDL text is large, and the question "what
        did this get created as" is always asked of a specific thing.
        """
        from ..expression.introspection import DDLStatementQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return DDLStatementQueryStatement(
            self.dialect,
            schema=target_schema,
            object_name=object_name,
            object_type=object_type,
        )

    def column_data_profile_statement(
        self, *, schema: Optional[str], table_name: str, columns: Sequence[str] = ()
    ) -> "ColumnDataProfileQueryStatement":
        """Return the statement that profiles every column of one table.

        ``table_name`` is required and there is no single-column form: a
        statistics catalogue answers for a whole table at once, and a
        per-column signature would make a caller loop a table's columns for
        data the engine already had together.

        ``columns`` is passed through for engines that must aggregate rather
        than read a catalogue -- see the expression's own docstring for why
        those cannot do without it.
        """
        from ..expression.introspection import ColumnDataProfileQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ColumnDataProfileQueryStatement(
            self.dialect, table_name=table_name, schema=target_schema, columns=columns
        )

    def column_value_sample_statement(
        self,
        *,
        schema: Optional[str],
        table_name: str,
        column_name: str,
        limit: int = VALUE_SAMPLE_LIMIT,
    ) -> "ColumnValueSampleQueryStatement":
        """Return the statement that lists a column's most frequent values.

        ``limit`` is an upper bound, not a promise -- an engine keeping a
        fixed-size most-common-values list returns what it kept. The default
        is the expression's own; see
        :data:`~...introspection.defaults.VALUE_SAMPLE_LIMIT`.
        """
        from ..expression.introspection import ColumnValueSampleQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return ColumnValueSampleQueryStatement(
            self.dialect,
            table_name=table_name,
            column_name=column_name,
            limit=limit,
            schema=target_schema,
        )

    def join_coverage_statement(
        self,
        *,
        schema: Optional[str],
        left_table: str,
        left_column: str,
        right_table: str,
        right_column: str,
    ) -> "JoinCoverageQueryStatement":
        """Return the statement that measures two columns' domain overlap.

        Both sides are named because the question is a relation between two
        objects rather than a fact about one -- the only family here of that
        shape.
        """
        from ..expression.introspection import JoinCoverageQueryStatement

        target_schema = schema if schema is not None else self.default_schema
        return JoinCoverageQueryStatement(
            self.dialect,
            left_table=left_table,
            left_column=left_column,
            right_table=right_table,
            right_column=right_column,
            schema=target_schema,
        )

    # ------------------------------------------------------------------ #
    # Cache — the manager's own service contract
    # ------------------------------------------------------------------ #

    @property
    def cache(self) -> IntrospectionCache:
        """The result cache this manager owns.

        Exposed so a caller can read or replace what the manager caches
        with -- an implementation that expires differently, or does not
        cache at all, is a legitimate choice and this is where it goes.
        Replacing it drops nothing: the new cache simply starts empty.
        """
        return self._cache

    @cache.setter
    def cache(self, value: IntrospectionCache) -> None:
        self._cache = value

    def invalidate_cache(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Drop cached results, from everything down to one object.

        Kept on the manager rather than pushed onto the caller because
        invalidation is part of what the service promises after a
        schema change, not a detail of how the cache stores things.
        """
        self._cache.invalidate(scope=scope, name=name)

    def clear_cache(self) -> None:
        """Drop every cached result, whatever its scope."""
        self._cache.clear()

    # ------------------------------------------------------------------ #
    # Parsing — turns the rows a database returned into results
    # ------------------------------------------------------------------ #

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O, shared by sync and async paths
    # Subclasses MUST implement these.
    # ------------------------------------------------------------------ #

    @abstractmethod
    def parse_database_info(self, rows: List[Dict[str, Any]]) -> IntrospectionDatabaseInfo:
        """Parse database info from query result rows."""
        ...

    @abstractmethod
    def parse_tables(self, rows: List[Dict[str, Any]], schema: Optional[str]) -> List[IntrospectionTableInfo]:
        """Parse table list from query result rows."""
        ...

    @abstractmethod
    def parse_columns(self, rows: List[Dict[str, Any]], table_name: str, schema: str) -> List[IntrospectionColumnInfo]:
        """Parse column list from query result rows."""
        ...

    @abstractmethod
    def parse_indexes(self, rows: List[Dict[str, Any]], table_name: str, schema: str) -> List[IndexInfo]:
        """Parse index list from query result rows."""
        ...

    @abstractmethod
    def parse_foreign_keys(self, rows: List[Dict[str, Any]], table_name: str, schema: str) -> List[IntrospectionForeignKeyInfo]:
        """Parse foreign key list from query result rows."""
        ...

    @abstractmethod
    def parse_views(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionViewInfo]:
        """Parse view list from query result rows."""
        ...

    @abstractmethod
    def parse_view_info(self, rows: List[Dict[str, Any]], view_name: str, schema: str) -> Optional[IntrospectionViewInfo]:
        """Parse view info from query result rows."""
        ...

    @abstractmethod
    def parse_triggers(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionTriggerInfo]:
        """Parse trigger rows into trigger information objects."""
        ...

    def parse_unused_indexes(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
    ) -> List[UnusedIndexInfo]:
        """Project the rows of an unused-indexes listing.

        Column names are read by both spellings because engines disagree even
        on whether the schema is a column of its own, and a key that is simply
        absent yields ``""`` rather than raising: a listing that omits an
        address component is still a listing, while one exception here would
        drop every row with it.
        """
        found: List[UnusedIndexInfo] = []
        for row in rows or []:
            row_schema = row.get("schema_name") or row.get("schema") or schema
            table = row.get("table_name") or row.get("table") or row.get("object_name") or ""
            index = row.get("index_name") or row.get("index") or row.get("object_name") or ""
            if not table or not index:
                continue
            found.append(
                UnusedIndexInfo(
                    schema=row_schema,
                    table_name=table,
                    index_name=index,
                    extra={
                        key: value
                        for key, value in row.items()
                        if key
                        not in {
                            "schema",
                            "schema_name",
                            "table",
                            "table_name",
                            "index",
                            "index_name",
                            "object_name",
                        }
                        and value is not None
                    },
                )
            )
        return found

    def parse_runtime_metrics(
        self,
        rows: List[Dict[str, Any]],
    ) -> List[RuntimeMetricItem]:
        """Project runtime-measurement rows into the narrow shape.

        Both spellings of a value are read (``value`` / ``metric_value``)
        because engines name the column after the concept rather than after
        the type. The ``kind`` slot is left ``None`` unless the row already
        names one: guessing whether a counter is throughput or latency from
        its name would be the engine's statistics pretending to be insight.
        """
        found: List[RuntimeMetricItem] = []
        for row in rows or []:
            name = row.get("name") or row.get("metric_name") or row.get("stat_name")
            if not name:
                continue
            value = row.get("value")
            if value is None:
                value = row.get("metric_value")
            if value is None:
                value = row.get("stat_value")
            known = {"name", "metric_name", "stat_name", "value", "metric_value", "stat_value"}
            found.append(
                RuntimeMetricItem(
                    name=str(name),
                    value=value,
                    kind=row.get("kind"),
                    unit=row.get("unit"),
                    description=row.get("description") or row.get("desc"),
                    source=row.get("source") or row.get("window"),
                    extra={
                        k: v for k, v in row.items() if k not in known and v is not None
                    },
                )
            )
        return found

    def parse_index_usage_stats(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
    ) -> List[IndexUsageStats]:
        """Project per-index counter rows, leaving unmeasured slots None."""
        found: List[IndexUsageStats] = []

        def _first_int(row: Dict[str, Any], *keys: str) -> Optional[int]:
            """The first named counter present, or None when none is."""
            for key in keys:
                v = row.get(key)
                if v is not None:
                    return int(v)
            return None

        for row in rows or []:
            row_schema = row.get("schema_name") or row.get("schema") or schema
            table = row.get("table_name") or row.get("relname") or row.get("table") or ""
            index = row.get("index_name") or row.get("indexrelname") or row.get("index") or ""
            if not table or not index:
                continue

            known = {
                "schema", "schema_name", "table", "table_name", "relname",
                "index", "index_name", "indexrelname",
                "idx_scan", "scans", "index_scans",
                "idx_tup_read", "rows_read", "rows_fetched", "idx_tup_fetch",
                "index_size_bytes", "size_bytes",
            }
            found.append(
                IndexUsageStats(
                    schema=row_schema,
                    table_name=table,
                    index_name=index,
                    scans=_first_int(row, "idx_scan", "scans", "index_scans"),
                    rows_read=_first_int(row, "idx_tup_read", "rows_read"),
                    rows_fetched=_first_int(row, "idx_tup_fetch", "rows_fetched"),
                    size_bytes=_first_int(row, "index_size_bytes", "size_bytes"),
                    extra={k: v for k, v in row.items() if k not in known and v is not None},
                )
            )
        return found

    def parse_object_dependencies(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
    ) -> List[ObjectDependency]:
        """Project dependency edges, reading both spellings of each address."""
        found: List[ObjectDependency] = []
        for row in rows or []:
            dependent = (
                row.get("dependent_name")
                or row.get("dependent")
                or row.get("object_name")
                or ""
            )
            referenced = row.get("referenced_name") or row.get("referenced") or ""
            if not dependent or not referenced:
                continue

            dependent_schema = (
                row.get("dependent_schema")
                or row.get("dependent_schema_name")
                or row.get("schema")
                or schema
            )
            found.append(
                ObjectDependency(
                    schema=row.get("schema_name") or row.get("schema") or schema,
                    dependent_schema=dependent_schema,
                    dependent=str(dependent),
                    dependent_type=row.get("dependent_type") or row.get("type"),
                    referenced=str(referenced),
                    referenced_type=row.get("referenced_type"),
                    kind=row.get("kind") or row.get("dependency_type"),
                    action=row.get("action") or row.get("on_delete"),
                    extra={
                        k: v
                        for k, v in row.items()
                        if v is not None
                        and k
                        not in {
                            "schema", "schema_name",
                            "dependent_schema", "dependent_schema_name",
                            "dependent", "dependent_name", "object_name", "dependent_type", "type",
                            "referenced", "referenced_name", "referenced_type",
                            "kind", "dependency_type", "action", "on_delete",
                        }
                    },
                )
            )
        return found

    def parse_ddl_statements(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
    ) -> List[DDLStatement]:
        """Project DDL rows; a row carrying no text is skipped, not raised.

        An engine that can name an object but not reproduce its DDL would
        produce exactly such a row, and the honest answer for it is the empty
        list -- the caller asked for text, and silently returning a row with a
        ``None`` text invites a reader to treat absence as a value.
        """
        found: List[DDLStatement] = []
        for row in rows or []:
            ddl = row.get("ddl") or row.get("sql") or row.get("definition")
            if not ddl:
                continue
            found.append(
                DDLStatement(
                    schema=row.get("schema_name") or row.get("schema") or schema,
                    object_type=row.get("object_type") or row.get("type"),
                    object_name=str(row.get("object_name") or row.get("name") or ""),
                    ddl=str(ddl),
                    native=row.get("native"),
                    extra={
                        k: v
                        for k, v in row.items()
                        if v is not None
                        and k
                        not in {
                            "schema", "schema_name", "object_type", "type",
                            "object_name", "name", "ddl", "sql", "definition", "native",
                        }
                    },
                )
            )
        return found

    def parse_table_usage_stats(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
    ) -> List[TableUsageStats]:
        """Project usage-counter rows into the common shape.

        Engines name their counters differently and track different subsets;
        each slot reads by every spelling this codebase has met, and stays
        ``None`` when no spelling is present -- an engine that does not track
        a counter is answering honestly by leaving it out, and a zero it
        never measured would be a lie of a different kind.
        """
        found: List[TableUsageStats] = []

        def _first_int(row: Dict[str, Any], *keys: str) -> Optional[int]:
            """The first named counter present, or None when none is."""
            for key in keys:
                value = row.get(key)
                if value is not None:
                    return int(value)
            return None

        for row in rows or []:
            row_schema = row.get("schema_name") or row.get("schema") or schema
            table = row.get("table_name") or row.get("table") or row.get("relname") or ""
            if not table:
                continue

            known = {
                "schema",
                "schema_name",
                "table",
                "table_name",
                "relname",
                "seq_scan",
                "sequential_scans",
                "idx_scan",
                "indexed_scans",
                "index_scans",
                "n_tup_ins",
                "inserts",
                "n_tup_upd",
                "updates",
                "n_tup_del",
                "deletes",
                "n_live_tup",
                "estimated_row_count",
                "table_rows",
            }
            found.append(
                TableUsageStats(
                    schema=row_schema,
                    table_name=table,
                    sequential_scans=_first_int(row, "seq_scan", "sequential_scans"),
                    indexed_scans=_first_int(row, "idx_scan", "indexed_scans", "index_scans"),
                    inserts=_first_int(row, "n_tup_ins", "inserts"),
                    updates=_first_int(row, "n_tup_upd", "updates"),
                    deletes=_first_int(row, "n_tup_del", "deletes"),
                    estimated_row_count=_first_int(row, "n_live_tup", "estimated_row_count", "table_rows"),
                    extra={
                        key: value
                        for key, value in row.items()
                        if key not in known and value is not None
                    },
                )
            )
        return found

    def parse_column_data_profiles(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
        table_name: str,
    ) -> List[ColumnDataProfile]:
        """Project a table's per-column profile rows.

        Slot names are read under both spellings engines use, and a figure the
        engine did not project stays ``None`` -- that is the engine saying "I
        do not measure this", which must not be smoothed into a zero.

        ``source`` is read as a word and written as a
        :class:`~...introspection.types.ProfileSource` member, because that is
        the slot's annotation and a word is not a member: the two compare
        equal, so a test written against ``==`` cannot tell them apart. The
        parser is where the engine's spelling becomes the closed set's own.

        ``row_count`` doubles as the sample size when ``source`` is a sample,
        which is why the two travel together rather than as separate fields.
        """
        found: List[ColumnDataProfile] = []

        def _first(row: Dict[str, Any], *keys: str) -> Any:
            for key in keys:
                if key in row and row[key] is not None:
                    return row[key]
            return None

        def _source(value: Any) -> Optional[ProfileSource]:
            """The member *value* names, or ``None`` when the engine said nothing.

            ``ProfileSource(value)`` is the Enum's own lookup over the closed
            set it declares, which is why there is no table beside it mapping
            words to members: such a table would be a second place that has to
            stay in step with the member list, which is the defect this
            repository just spent a change removing. A member is returned
            unchanged, so a caller that already holds one is not re-resolved.

            A word the set does not name raises rather than being smoothed
            into ``UNKNOWN``. ``UNKNOWN`` is the engine declining to say how it
            measured, which is a fact; a misspelled ``"agregate"`` is nobody's
            fact, and writing ``UNKNOWN`` over it would hide the typo the rule
            is about -- a value nothing validates. This parser is the boundary
            an engine's word crosses, so it is the place that validates it.
            """
            if value is None:
                return None
            return ProfileSource(value)

        for row in rows or []:
            column = _first(row, "column_name", "attname", "column")
            if not column:
                continue
            nulls = _first(row, "null_fraction", "null_frac", "null_ratio")
            distinct = _first(row, "distinct_count", "n_distinct", "num_distinct")
            rows_in_profile = _first(row, "row_count", "rows", "n_live_tup", "num_rows")
            if nulls is None:
                # An aggregating dialect can count nulls more cheaply than it
                # can divide by a row count it may report as zero; the fraction
                # is derived here so both shapes land in one slot.
                null_count = _first(row, "null_count", "num_nulls")
                if null_count is not None and rows_in_profile:
                    nulls = float(null_count) / float(rows_in_profile)
            known = {
                "schema", "schema_name",
                "table", "table_name", "relname",
                "column", "column_name", "attname",
                "null_fraction", "null_frac", "null_ratio",
                "null_count", "num_nulls",
                "distinct_count", "n_distinct", "num_distinct",
                "min_value", "min", "low_value",
                "max_value", "max", "high_value",
                "row_count", "rows", "n_live_tup", "num_rows",
                "source", "collected_at", "last_analyzed", "last_analyze",
            }
            found.append(
                ColumnDataProfile(
                    schema=_first(row, "schema_name", "schema") or schema,
                    table_name=_first(row, "table_name", "relname", "table") or table_name,
                    column_name=str(column),
                    null_fraction=float(nulls) if nulls is not None else None,
                    distinct_count=int(distinct) if distinct is not None else None,
                    min_value=_first(row, "min_value", "min", "low_value"),
                    max_value=_first(row, "max_value", "max", "high_value"),
                    row_count=rows_in_profile,
                    source=_source(_first(row, "source")),
                    collected_at=_first(row, "collected_at", "last_analyzed", "last_analyze"),
                    extra={
                        key: value
                        for key, value in row.items()
                        if key not in known and value is not None
                    },
                )
            )
        return found

    def parse_column_value_samples(
        self,
        rows: List[Dict[str, Any]],
    ) -> List[ColumnValueFrequency]:
        """Project a value listing.

        A row's value may legitimately be ``None`` -- NULL is often the most
        interesting member of a column's domain -- so the "skip when empty"
        rule applied to addresses does **not** apply here.
        """
        found: List[ColumnValueFrequency] = []
        for row in rows or []:
            if not any(k in row for k in ("value", "val", "most_common_val")):
                continue
            value = row.get("value")
            if value is None:
                value = row.get("val")
            if value is None and "most_common_val" in row:
                value = row.get("most_common_val")
            count = row.get("count")
            if count is None:
                count = row.get("n")
            frequency = row.get("frequency")
            if frequency is None:
                frequency = row.get("most_common_freq")
            known = {
                "value", "val", "most_common_val",
                "count", "n",
                "frequency", "most_common_freq",
            }
            found.append(
                ColumnValueFrequency(
                    value=value,
                    count=int(count) if count is not None else None,
                    frequency=float(frequency) if frequency is not None else None,
                    extra={
                        key: v
                        for key, v in row.items()
                        if key not in known and v is not None
                    },
                )
            )
        return found

    def parse_join_coverage(
        self,
        rows: List[Dict[str, Any]],
        *,
        left_table: str,
        left_column: str,
        right_table: str,
        right_column: str,
        schema: Optional[str] = None,
    ) -> Optional[JoinCoverage]:
        """Project the single row an overlap measurement returns.

        ``None`` when the answer carries no row: an engine that could not
        compute the measurement is answering "no measurement", which a caller
        must be able to tell apart from "zero overlap".
        """
        for row in rows or []:
            left = row.get("left_coverage")
            if left is None:
                left = row.get("left_fraction")
            right = row.get("right_coverage")
            if right is None:
                right = row.get("right_fraction")
            if left is None and right is None:
                continue
            return JoinCoverage(
                left_schema=schema,
                left_table=left_table,
                left_column=left_column,
                right_schema=schema,
                right_table=right_table,
                right_column=right_column,
                left_coverage=float(left) if left is not None else None,
                right_coverage=float(right) if right is not None else None,
                extra={
                    key: value
                    for key, value in row.items()
                    if key
                    not in {
                        "left_coverage", "left_fraction",
                        "right_coverage", "right_fraction",
                    }
                    and value is not None
                },
            )
        return None


class AbstractIntrospector(IntrospectorBase, ABC):
    """Abstract base class for synchronous database introspectors.

    This class provides all synchronous I/O methods for database introspection.
    Subclasses must implement all parse_* methods.

    Public API:
        get_database_info(), list_tables(), get_table_info(), table_exists(),
        list_columns(), get_column_info(), column_exists(), list_indexes(),
        get_index_info(), get_primary_key(), list_foreign_keys(),
        get_foreign_key_info(), list_views(), get_view_info(), view_exists(),
        list_triggers(), get_trigger_info()

        Cache: invalidate_cache(), clear_cache()
    """

    def __init__(
        self,
        backend: Any,
        executor: "IntrospectorExecutor",
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)

    # ------------------------------------------------------------------ #
    # Public synchronous API
    # ------------------------------------------------------------------ #

    def get_database_info(self) -> IntrospectionDatabaseInfo:
        """Return basic information about the connected database."""
        key = self._cache.key(IntrospectionScope.DATABASE)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.database_info_statement().to_sql()
        result = self.parse_database_info(self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[IntrospectionTableInfo]:
        """List tables (and optionally views/system tables) in the database."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.table_list_statement(
            schema=schema,
            include_system=include_system,
            include_views=True,
            table_type=table_type,
        ).to_sql()
        result = self.parse_tables(self._executor.execute(sql, params), schema)
        self._cache.set(key, result)
        return result

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        """Return detailed information for a specific table, including columns,
        indexes, and foreign keys."""
        key = self._cache.key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        table = next((t for t in self.list_tables(schema) if t.name == table_name), None)
        if table is None:
            return None
        table.columns = self.list_columns(table_name, schema)
        table.indexes = self.list_indexes(table_name, schema)
        table.foreign_keys = self.list_foreign_keys(table_name, schema)
        self._cache.set(key, table)
        return table

    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named table exists."""
        return self.get_table_info(table_name, schema) is not None

    def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionColumnInfo]:
        """List all columns of the given table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.column_info_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_columns(self._executor.execute(sql, params), table_name, target)
        self._cache.set(key, result)
        return result

    def get_column_info(self, table_name: str, column_name: str, schema: Optional[str] = None) -> Optional[IntrospectionColumnInfo]:
        """Return information for a specific column, or None if not found."""
        return next(
            (c for c in self.list_columns(table_name, schema) if c.name == column_name),
            None,
        )

    def column_exists(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named column exists in the given table."""
        return self.get_column_info(table_name, column_name, schema) is not None

    def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of the given table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.index_info_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_indexes(self._executor.execute(sql, params), table_name, target)
        self._cache.set(key, result)
        return result

    def get_index_info(self, table_name: str, index_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Return information for a specific index, or None if not found."""
        return next(
            (i for i in self.list_indexes(table_name, schema) if i.name == index_name),
            None,
        )

    def get_primary_key(self, table_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Return the primary key index for the given table, or None."""
        return next(
            (i for i in self.list_indexes(table_name, schema) if i.is_primary),
            None,
        )

    def list_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionForeignKeyInfo]:
        """List all foreign keys of the given table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.foreign_key_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_foreign_keys(self._executor.execute(sql, params), table_name, target)
        self._cache.set(key, result)
        return result

    def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[IntrospectionForeignKeyInfo]:
        """Return information for a specific foreign key, or None if not found."""
        return next(
            (fk for fk in self.list_foreign_keys(table_name, schema) if fk.name == fk_name),
            None,
        )

    def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[IntrospectionViewInfo]:
        """List all views in the database."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.VIEW, schema=schema, extra=str(include_system))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.view_list_statement(schema=schema, include_system=include_system).to_sql()
        result = self.parse_views(self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    def get_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[IntrospectionViewInfo]:
        """Return detailed information for a specific view, or None if not found."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.view_info_statement(view_name=view_name, schema=schema).to_sql()
        result = self.parse_view_info(self._executor.execute(sql, params), view_name, target)
        if result is not None:
            self._cache.set(key, result)
        return result

    def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named view exists."""
        return self.get_view_info(view_name, schema) is not None

    def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[IntrospectionTriggerInfo]:
        """List all triggers, optionally filtered by table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.TRIGGER, table_name or "*", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.trigger_list_statement(schema=schema, table_name=table_name).to_sql()
        result = self.parse_triggers(self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    def list_unused_indexes(
        self,
        schema: Optional[str] = None,
    ) -> List[UnusedIndexInfo]:
        """List the indexes this engine reports as never having served a query.

        Returns an empty list for an engine that cannot answer -- ``False``
        from the dialect's capability probe is what the caller checks first,
        and an engine that answers but has nothing to report also returns
        empty. The two are indistinguishable here, which is why the docstring
        of :class:`UnusedIndexInfo` says what absence does and does not prove.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, "unused", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.unused_indexes_statement(schema=schema).to_sql()
        result = self.parse_unused_indexes(self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    def list_table_usage_stats(
        self,
        schema: Optional[str] = None,
    ) -> List[TableUsageStats]:
        """Read every table's usage counters, as the engine last counted them.

        Empty for an engine that cannot answer, same rule as
        :meth:`list_unused_indexes`. Every counter returned is *since the
        statistics were last reset*, on the engine's own schedule -- the
        number answers "how much has happened in the window the engine
        remembers", and nothing more.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.TABLE, "usage_stats", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.table_usage_stats_statement(schema=schema).to_sql()
        result = self.parse_table_usage_stats(self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    def list_column_data_profiles(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ColumnDataProfile]:
        """Profile every column of one table from the data itself.

        The counterpart of :meth:`list_columns`, which reports what a column
        *promises*; this reports what it *holds*, and the two disagreeing is
        the useful signal. Every figure may be ``None``, and ``source`` says
        whether what came back is an estimate or a count -- a caller comparing
        profiles across engines must read it.

        Empty for an engine that cannot answer.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(
            IntrospectionScope.COLUMN, table_name, "data_profile", schema=schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        # The catalogue already knows the column names, and an aggregating
        # dialect needs them to pivot its aggregates; a catalogue-based one
        # ignores the list. One cheap query either way.
        columns = tuple(column.name for column in self.list_columns(table_name, schema))
        sql, params = self.column_data_profile_statement(
            schema=schema, table_name=table_name, columns=columns
        ).to_sql()
        result = self.parse_column_data_profiles(
            self._executor.execute(sql, params), target, table_name
        )
        self._cache.set(key, result)
        return result

    def sample_column_values(
        self,
        table_name: str,
        column_name: str,
        limit: int = VALUE_SAMPLE_LIMIT,
        schema: Optional[str] = None,
    ) -> List[ColumnValueFrequency]:
        """List a column's most frequent values, up to ``limit``.

        Fewer than ``limit`` is a correct answer: an engine that keeps a
        fixed-size most-common-values list returns what it kept, and padding
        the list would invent values. The default is the expression's own;
        see :data:`~...introspection.defaults.VALUE_SAMPLE_LIMIT`.
        """
        key = self._cache.key(
            IntrospectionScope.COLUMN,
            table_name,
            column_name,
            "values",
            limit,
            schema=schema,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.column_value_sample_statement(
            schema=schema, table_name=table_name, column_name=column_name, limit=limit
        ).to_sql()
        result = self.parse_column_value_samples(self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    def estimate_join_coverage(
        self,
        left_table: str,
        left_column: str,
        right_table: str,
        right_column: str,
        schema: Optional[str] = None,
    ) -> Optional[JoinCoverage]:
        """Measure how much two columns' distinct value domains overlap.

        ``None`` when the engine cannot measure it -- which is not the same
        answer as "zero overlap", and a caller deciding whether a join is
        worth writing needs to tell them apart.

        Both fractions are estimates: NULLs are excluded on both sides,
        collations are not reconciled, and the engine may sample. A high
        coverage is evidence of a join, not proof of one.
        """
        key = self._cache.key(
            IntrospectionScope.COLUMN,
            left_table,
            left_column,
            "join_coverage",
            right_table,
            right_column,
            schema=schema,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.join_coverage_statement(
            schema=schema,
            left_table=left_table,
            left_column=left_column,
            right_table=right_table,
            right_column=right_column,
        ).to_sql()
        result = self.parse_join_coverage(
            self._executor.execute(sql, params),
            left_table=left_table,
            left_column=left_column,
            right_table=right_table,
            right_column=right_column,
            schema=schema if schema is not None else self.default_schema,
        )
        self._cache.set(key, result)
        return result

    def list_runtime_metrics(
        self,
        schema: Optional[str] = None,
    ) -> List[RuntimeMetricItem]:
        """Read the engine's live runtime measurements.

        Every number is *since the window the engine remembers*; the window is
        the engine's to state and lands in each item's ``source``. An engine
        that cannot answer returns empty, same rule as the other families.
        """
        key = self._cache.key(IntrospectionScope.DATABASE, "runtime", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.runtime_metrics_statement(schema=schema).to_sql()
        result = self.parse_runtime_metrics(self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    def list_index_usage_stats(
        self,
        schema: Optional[str] = None,
    ) -> List[IndexUsageStats]:
        """Read per-index use counters, answering "how much" rather than "ever"."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, "usage_stats", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.index_usage_stats_statement(schema=schema).to_sql()
        result = self.parse_index_usage_stats(self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    def list_object_dependencies(
        self,
        object_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[ObjectDependency]:
        """Read the object dependency graph, or one object's dependants.

        ``object_name`` answers "what breaks if I drop this"; omitted, the
        answer is the whole graph, which is larger and slower.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(
            IntrospectionScope.TABLE, object_name or "*", "dependencies", schema=schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.object_dependency_statement(
            schema=schema, object_name=object_name
        ).to_sql()
        result = self.parse_object_dependencies(self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    def get_ddl_statement(
        self,
        object_name: str,
        object_type: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Optional[DDLStatement]:
        """Read the DDL that recreates one object, or None when the engine won't.

        An engine without native retrieval answers UnsupportedFeatureError
        rather than being handed an assembly that looks authoritative.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(
            IntrospectionScope.TABLE, object_name, "ddl", schema=schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached[0] if cached else None
        sql, params = self.ddl_statement_statement(
            schema=schema, object_name=object_name, object_type=object_type
        ).to_sql()
        found = self.parse_ddl_statements(self._executor.execute(sql, params), target)
        self._cache.set(key, found)
        return found[0] if found else None

    def get_trigger_info(self, trigger_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTriggerInfo]:
        """Return information for a specific trigger, or None if not found."""
        return next(
            (t for t in self.list_triggers(schema=schema) if t.name == trigger_name),
            None,
        )


class AsyncAbstractIntrospector(IntrospectorBase, ABC):
    """Abstract base class for asynchronous database introspectors.

    This class provides all asynchronous I/O methods for database introspection.
    Subclasses must implement all parse_* methods.

    Public API (all methods are async, names match sync version):
        get_database_info(), list_tables(), get_table_info(), table_exists(),
        list_columns(), get_column_info(), column_exists(), list_indexes(),
        get_index_info(), get_primary_key(), list_foreign_keys(),
        get_foreign_key_info(), list_views(), get_view_info(), view_exists(),
        list_triggers(), get_trigger_info()

        Cache (synchronous): invalidate_cache(), clear_cache()
    """

    def __init__(
        self,
        backend: Any,
        executor: "AsyncIntrospectorExecutor",
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)

    # ------------------------------------------------------------------ #
    # Public asynchronous API
    # Method names match the sync version (no _async suffix).
    # ------------------------------------------------------------------ #

    async def get_database_info(self) -> IntrospectionDatabaseInfo:
        """Return basic information about the connected database."""
        key = self._cache.key(IntrospectionScope.DATABASE)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.database_info_statement().to_sql()
        result = self.parse_database_info(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    async def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[IntrospectionTableInfo]:
        """List tables (and optionally views/system tables) in the database."""
        key = self._cache.key(
            IntrospectionScope.TABLE,
            schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.table_list_statement(
            schema=schema,
            include_system=include_system,
            include_views=True,
            table_type=table_type,
        ).to_sql()
        result = self.parse_tables(await self._executor.execute(sql, params), schema)
        self._cache.set(key, result)
        return result

    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        """Return detailed information for a specific table, including columns,
        indexes, and foreign keys."""
        key = self._cache.key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        table = next(
            (t for t in await self.list_tables(schema) if t.name == table_name),
            None,
        )
        if table is None:
            return None
        table.columns = await self.list_columns(table_name, schema)
        table.indexes = await self.list_indexes(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys(table_name, schema)
        self._cache.set(key, table)
        return table

    async def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named table exists."""
        return await self.get_table_info(table_name, schema) is not None

    async def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionColumnInfo]:
        """List all columns of the given table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.column_info_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_columns(await self._executor.execute(sql, params), table_name, target)
        self._cache.set(key, result)
        return result

    async def get_column_info(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> Optional[IntrospectionColumnInfo]:
        """Return information for a specific column, or None if not found."""
        return next(
            (c for c in await self.list_columns(table_name, schema) if c.name == column_name),
            None,
        )

    async def column_exists(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named column exists in the given table."""
        return await self.get_column_info(table_name, column_name, schema) is not None

    async def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of the given table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.index_info_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_indexes(await self._executor.execute(sql, params), table_name, target)
        self._cache.set(key, result)
        return result

    async def get_index_info(
        self, table_name: str, index_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Return information for a specific index, or None if not found."""
        return next(
            (i for i in await self.list_indexes(table_name, schema) if i.name == index_name),
            None,
        )

    async def get_primary_key(self, table_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Return the primary key index for the given table, or None."""
        return next(
            (i for i in await self.list_indexes(table_name, schema) if i.is_primary),
            None,
        )

    async def list_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionForeignKeyInfo]:
        """List all foreign keys of the given table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.foreign_key_statement(table_name=table_name, schema=schema).to_sql()
        result = self.parse_foreign_keys(await self._executor.execute(sql, params), table_name, target)
        self._cache.set(key, result)
        return result

    async def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[IntrospectionForeignKeyInfo]:
        """Return information for a specific foreign key, or None if not found."""
        return next(
            (fk for fk in await self.list_foreign_keys(table_name, schema) if fk.name == fk_name),
            None,
        )

    async def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[IntrospectionViewInfo]:
        """List all views in the database."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.VIEW, schema=schema, extra=str(include_system))
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.view_list_statement(schema=schema, include_system=include_system).to_sql()
        result = self.parse_views(await self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    async def get_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[IntrospectionViewInfo]:
        """Return detailed information for a specific view, or None if not found."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.view_info_statement(view_name=view_name, schema=schema).to_sql()
        result = self.parse_view_info(await self._executor.execute(sql, params), view_name, target)
        if result is not None:
            self._cache.set(key, result)
        return result

    async def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named view exists."""
        return await self.get_view_info(view_name, schema) is not None

    async def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[IntrospectionTriggerInfo]:
        """List all triggers, optionally filtered by table."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.TRIGGER, table_name or "*", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.trigger_list_statement(schema=schema, table_name=table_name).to_sql()
        result = self.parse_triggers(await self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    async def list_unused_indexes(
        self,
        schema: Optional[str] = None,
    ) -> List[UnusedIndexInfo]:
        """List the indexes this engine reports as never having served a query.

        The async twin's copy; identical to the sync one apart from the await,
        and kept word-for-word so the two cannot drift on what absence means.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, "unused", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.unused_indexes_statement(schema=schema).to_sql()
        result = self.parse_unused_indexes(await self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    async def list_table_usage_stats(
        self,
        schema: Optional[str] = None,
    ) -> List[TableUsageStats]:
        """Read every table's usage counters; the async twin's copy.

        Identical to the sync one apart from the await, so the two cannot
        drift on what a counter counts.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.TABLE, "usage_stats", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.table_usage_stats_statement(schema=schema).to_sql()
        result = self.parse_table_usage_stats(await self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    async def list_column_data_profiles(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ColumnDataProfile]:
        """Profile every column of one table; the async twin's copy.

        Identical to the sync one apart from the await, so the two cannot
        disagree about what ``source`` means.
        """
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(
            IntrospectionScope.COLUMN, table_name, "data_profile", schema=schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        columns = tuple(
            column.name for column in await self.list_columns(table_name, schema)
        )
        sql, params = self.column_data_profile_statement(
            schema=schema, table_name=table_name, columns=columns
        ).to_sql()
        result = self.parse_column_data_profiles(
            await self._executor.execute(sql, params), target, table_name
        )
        self._cache.set(key, result)
        return result

    async def sample_column_values(
        self,
        table_name: str,
        column_name: str,
        limit: int = VALUE_SAMPLE_LIMIT,
        schema: Optional[str] = None,
    ) -> List[ColumnValueFrequency]:
        """List a column's most frequent values; the async twin's copy."""
        key = self._cache.key(
            IntrospectionScope.COLUMN,
            table_name,
            column_name,
            "values",
            limit,
            schema=schema,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.column_value_sample_statement(
            schema=schema, table_name=table_name, column_name=column_name, limit=limit
        ).to_sql()
        result = self.parse_column_value_samples(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    async def estimate_join_coverage(
        self,
        left_table: str,
        left_column: str,
        right_table: str,
        right_column: str,
        schema: Optional[str] = None,
    ) -> Optional[JoinCoverage]:
        """Measure two columns' domain overlap; the async twin's copy."""
        key = self._cache.key(
            IntrospectionScope.COLUMN,
            left_table,
            left_column,
            "join_coverage",
            right_table,
            right_column,
            schema=schema,
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.join_coverage_statement(
            schema=schema,
            left_table=left_table,
            left_column=left_column,
            right_table=right_table,
            right_column=right_column,
        ).to_sql()
        result = self.parse_join_coverage(
            await self._executor.execute(sql, params),
            left_table=left_table,
            left_column=left_column,
            right_table=right_table,
            right_column=right_column,
            schema=schema if schema is not None else self.default_schema,
        )
        self._cache.set(key, result)
        return result

    async def list_runtime_metrics(
        self,
        schema: Optional[str] = None,
    ) -> List[RuntimeMetricItem]:
        """Read the engine's live runtime measurements; the async twin's copy.

        Identical to the sync one apart from the await, so the two cannot
        disagree about what a zero covers.
        """
        key = self._cache.key(IntrospectionScope.DATABASE, "runtime", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.runtime_metrics_statement(schema=schema).to_sql()
        result = self.parse_runtime_metrics(await self._executor.execute(sql, params))
        self._cache.set(key, result)
        return result

    async def list_index_usage_stats(
        self,
        schema: Optional[str] = None,
    ) -> List[IndexUsageStats]:
        """Read per-index use counters; the async twin's copy."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, "usage_stats", schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.index_usage_stats_statement(schema=schema).to_sql()
        result = self.parse_index_usage_stats(await self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    async def list_object_dependencies(
        self,
        object_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[ObjectDependency]:
        """Read the object dependency graph; the async twin's copy."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(
            IntrospectionScope.TABLE, object_name or "*", "dependencies", schema=schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.object_dependency_statement(
            schema=schema, object_name=object_name
        ).to_sql()
        result = self.parse_object_dependencies(await self._executor.execute(sql, params), target)
        self._cache.set(key, result)
        return result

    async def get_ddl_statement(
        self,
        object_name: str,
        object_type: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> Optional[DDLStatement]:
        """Read one object's DDL; the async twin's copy."""
        target = schema if schema is not None else self.default_schema
        key = self._cache.key(
            IntrospectionScope.TABLE, object_name, "ddl", schema=schema
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached[0] if cached else None
        sql, params = self.ddl_statement_statement(
            schema=schema, object_name=object_name, object_type=object_type
        ).to_sql()
        found = self.parse_ddl_statements(await self._executor.execute(sql, params), target)
        self._cache.set(key, found)
        return found[0] if found else None

    async def get_trigger_info(self, trigger_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTriggerInfo]:
        """Return information for a specific trigger, or None if not found."""
        return next(
            (t for t in await self.list_triggers(schema=schema) if t.name == trigger_name),
            None,
        )
