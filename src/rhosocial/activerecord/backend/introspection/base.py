# src/rhosocial/activerecord/backend/introspection/base.py
"""
Abstract introspector base classes.

This module provides the abstract base classes for database introspection,
following the project's sync/async parity principle:

1. IntrospectorMixin: the shared base every introspector inherits, which
   knows the default schema. It holds no state, does no I/O and never sees
   a result row.

2. SyncAbstractIntrospector: Synchronous introspector with all I/O methods
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
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .cache import InMemoryIntrospectionCache, IntrospectionCache
from .types import (
    IntrospectionDatabaseInfo,
    IntrospectionTableInfo,
    IntrospectionColumnInfo,
    IndexInfo,
    IntrospectionForeignKeyInfo,
    IntrospectionViewInfo,
    IntrospectionTriggerInfo,
    IntrospectionScope,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase
    from ..expression.introspection import (
        ColumnInfoQueryStatement,
        DatabaseInfoQueryStatement,
        ForeignKeyQueryStatement,
        IndexInfoQueryStatement,
        TableListQueryStatement,
        TriggerListQueryStatement,
        ViewInfoQueryStatement,
        ViewListQueryStatement,
    )
    from .executor import SyncIntrospectorExecutor, AsyncIntrospectorExecutor


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
        """Parse trigger list from query result rows."""
        ...


class SyncAbstractIntrospector(IntrospectorBase, ABC):
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
        executor: "SyncIntrospectorExecutor",
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

    async def get_trigger_info(self, trigger_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTriggerInfo]:
        """Return information for a specific trigger, or None if not found."""
        return next(
            (t for t in await self.list_triggers(schema=schema) if t.name == trigger_name),
            None,
        )
