# src/rhosocial/activerecord/backend/introspection/base.py
"""
Abstract introspector base classes.

This module provides the abstract base classes for database introspection,
following the project's sync/async parity principle:

1. IntrospectorMixin: Shared non-I/O logic (cache management, SQL generation,
   _parse_* abstract method declarations)

2. SyncAbstractIntrospector: Synchronous introspector with all I/O methods
   being synchronous.

3. AsyncAbstractIntrospector: Asynchronous introspector with all I/O methods
   being async. Method names match the sync version (no _async suffix).

Design principles:
  - Sync and Async are separate and cannot coexist in the same class.
  - I/O methods have identical signatures between sync and async versions,
    differing only in async/await keywords.
  - Non-I/O methods (cache, SQL generation, parsing) are shared via mixin.
"""

import threading
import time
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from .types import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    ForeignKeyInfo,
    ViewInfo,
    TriggerInfo,
    IntrospectionScope,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase


class IntrospectorMixin:
    """Mixin providing shared non-I/O functionality for introspectors.

    This mixin contains:
    - Cache management (thread-safe with TTL support)
    - SQL generation methods (delegating to Expression + Dialect)
    - Abstract _parse_* method declarations (must be implemented by subclasses)
    - Helper methods for schema handling

    Both SyncAbstractIntrospector and AsyncAbstractIntrospector inherit
    from this mixin to share all non-I/O logic.
    """

    DEFAULT_CACHE_TTL: int = 300  # seconds

    def _init_introspector_state(self) -> None:
        """Initialize introspector state. Call from __init__."""
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl: int = self.DEFAULT_CACHE_TTL

    # ------------------------------------------------------------------ #
    # Dialect shortcut
    # ------------------------------------------------------------------ #

    @property
    def dialect(self) -> "SQLDialectBase":
        """Get the SQL dialect from the backend."""
        return self._backend.dialect

    def _get_default_schema(self) -> str:
        """Return the default schema name for this database.

        Subclasses should override to return the database-specific default
        (e.g. ``"main"`` for SQLite, ``"public"`` for PostgreSQL).
        Returns an empty string by default so generic callers can still work.
        """
        return ""

    # ------------------------------------------------------------------ #
    # Cache management (thread-safe, no I/O)
    # ------------------------------------------------------------------ #

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached value if not expired."""
        with self._cache_lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            data, ts = entry
            if time.time() - ts > self._cache_ttl:
                del self._cache[key]
                return None
            return data

    def _set_cached(self, key: str, data: Any) -> None:
        """Store value in cache with current timestamp."""
        with self._cache_lock:
            self._cache[key] = (data, time.time())

    def _make_cache_key(
        self,
        scope: IntrospectionScope,
        *args: str,
        schema: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> str:
        """Build a cache key from scope and optional parameters."""
        parts = [scope.value]
        if schema:
            parts.append(f"schema:{schema}")
        parts.extend(str(a) for a in args)
        if extra:
            parts.append(extra)
        return ":".join(parts)

    def invalidate_cache(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Invalidate cached introspection results.

        Args:
            scope: Scope to invalidate; None invalidates everything.
            name:  Object name within the scope to invalidate; None
                   invalidates all entries for the scope.
        """
        with self._cache_lock:
            if scope is None:
                self._cache.clear()
            elif name is None:
                sv = scope.value
                prefix = f"{sv}:"
                for k in [k for k in self._cache if k == sv or k.startswith(prefix)]:
                    del self._cache[k]
            else:
                sv = scope.value
                prefix = f"{sv}:"
                for k in [k for k in self._cache if (k == sv or k.startswith(prefix)) and name in k]:
                    del self._cache[k]

    def clear_cache(self) -> None:
        """Clear all cached introspection results."""
        with self._cache_lock:
            self._cache.clear()

    # ------------------------------------------------------------------ #
    # SQL generation — delegates to Expression + Dialect (no I/O)
    # Subclasses may override to use database-specific statements.
    # ------------------------------------------------------------------ #

    def _build_database_info_sql(self) -> Tuple[str, tuple]:
        """Build SQL for database information query."""
        from ..expression.introspection import DatabaseInfoExpression
        return DatabaseInfoExpression(self.dialect).to_sql()

    def _build_table_list_sql(
        self,
        schema: Optional[str],
        include_system: bool,
        include_views: bool = True,
        table_type: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """Build SQL for table list query."""
        from ..expression.introspection import TableListExpression
        expr = (
            TableListExpression(self.dialect)
            .include_system(include_system)
            .include_views(include_views)
        )
        if schema:
            expr = expr.schema(schema)
        if table_type:
            expr = expr.table_type(table_type)
        return expr.to_sql()

    def _build_column_info_sql(
        self, table_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        """Build SQL for column information query."""
        from ..expression.introspection import ColumnInfoExpression
        expr = ColumnInfoExpression(self.dialect, table_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_index_info_sql(
        self, table_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        """Build SQL for index information query."""
        from ..expression.introspection import IndexInfoExpression
        expr = IndexInfoExpression(self.dialect, table_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_foreign_key_sql(
        self, table_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        """Build SQL for foreign key query."""
        from ..expression.introspection import ForeignKeyExpression
        expr = ForeignKeyExpression(self.dialect, table_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_view_list_sql(
        self, schema: Optional[str], include_system: bool
    ) -> Tuple[str, tuple]:
        """Build SQL for view list query."""
        from ..expression.introspection import ViewListExpression
        expr = ViewListExpression(self.dialect).include_system(include_system)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_view_info_sql(
        self, view_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        """Build SQL for view information query."""
        from ..expression.introspection import ViewInfoExpression
        expr = ViewInfoExpression(self.dialect, view_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_trigger_list_sql(
        self, table_name: Optional[str], schema: Optional[str]
    ) -> Tuple[str, tuple]:
        """Build SQL for trigger list query."""
        from ..expression.introspection import TriggerListExpression
        expr = TriggerListExpression(self.dialect)
        if schema:
            expr = expr.schema(schema)
        if table_name:
            expr = expr.for_table(table_name)
        return expr.to_sql()

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O, shared by sync and async paths
    # Subclasses MUST implement these.
    # ------------------------------------------------------------------ #

    @abstractmethod
    def _parse_database_info(self, rows: List[Dict[str, Any]]) -> DatabaseInfo:
        """Parse database info from query result rows."""
        ...

    @abstractmethod
    def _parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[TableInfo]:
        """Parse table list from query result rows."""
        ...

    @abstractmethod
    def _parse_columns(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[ColumnInfo]:
        """Parse column list from query result rows."""
        ...

    @abstractmethod
    def _parse_indexes(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[IndexInfo]:
        """Parse index list from query result rows."""
        ...

    @abstractmethod
    def _parse_foreign_keys(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[ForeignKeyInfo]:
        """Parse foreign key list from query result rows."""
        ...

    @abstractmethod
    def _parse_views(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[ViewInfo]:
        """Parse view list from query result rows."""
        ...

    @abstractmethod
    def _parse_view_info(
        self, rows: List[Dict[str, Any]], view_name: str, schema: str
    ) -> Optional[ViewInfo]:
        """Parse view info from query result rows."""
        ...

    @abstractmethod
    def _parse_triggers(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[TriggerInfo]:
        """Parse trigger list from query result rows."""
        ...


class SyncAbstractIntrospector(IntrospectorMixin, ABC):
    """Abstract base class for synchronous database introspectors.

    This class provides all synchronous I/O methods for database introspection.
    Subclasses must implement all _parse_* methods.

    Public API:
        get_database_info(), list_tables(), get_table_info(), table_exists(),
        list_columns(), get_column_info(), column_exists(), list_indexes(),
        get_index_info(), get_primary_key(), list_foreign_keys(),
        get_foreign_key_info(), list_views(), get_view_info(), view_exists(),
        list_triggers(), get_trigger_info()

        Cache: invalidate_cache(), clear_cache()
    """

    def __init__(self, backend: Any, executor: "SyncIntrospectorExecutor") -> None:
        self._backend = backend
        self._executor = executor
        self._init_introspector_state()

    # ------------------------------------------------------------------ #
    # Public synchronous API
    # ------------------------------------------------------------------ #

    def get_database_info(self) -> DatabaseInfo:
        """Return basic information about the connected database."""
        key = self._make_cache_key(IntrospectionScope.DATABASE)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_database_info_sql()
        result = self._parse_database_info(self._executor.execute(sql, params))
        self._set_cached(key, result)
        return result

    def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """List tables (and optionally views/system tables) in the database."""
        key = self._make_cache_key(
            IntrospectionScope.TABLE, schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_table_list_sql(schema, include_system, True, table_type)
        result = self._parse_tables(self._executor.execute(sql, params), schema)
        self._set_cached(key, result)
        return result

    def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        """Return detailed information for a specific table, including columns,
        indexes, and foreign keys."""
        key = self._make_cache_key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        table = next(
            (t for t in self.list_tables(schema) if t.name == table_name), None
        )
        if table is None:
            return None
        table.columns = self.list_columns(table_name, schema)
        table.indexes = self.list_indexes(table_name, schema)
        table.foreign_keys = self.list_foreign_keys(table_name, schema)
        self._set_cached(key, table)
        return table

    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named table exists."""
        return self.get_table_info(table_name, schema) is not None

    def list_columns(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnInfo]:
        """List all columns of the given table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_column_info_sql(table_name, schema)
        result = self._parse_columns(
            self._executor.execute(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    def get_column_info(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> Optional[ColumnInfo]:
        """Return information for a specific column, or None if not found."""
        return next(
            (c for c in self.list_columns(table_name, schema) if c.name == column_name),
            None,
        )

    def column_exists(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> bool:
        """Return True if the named column exists in the given table."""
        return self.get_column_info(table_name, column_name, schema) is not None

    def list_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """List all indexes of the given table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_index_info_sql(table_name, schema)
        result = self._parse_indexes(
            self._executor.execute(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    def get_index_info(
        self, table_name: str, index_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Return information for a specific index, or None if not found."""
        return next(
            (i for i in self.list_indexes(table_name, schema) if i.name == index_name),
            None,
        )

    def get_primary_key(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Return the primary key index for the given table, or None."""
        return next(
            (i for i in self.list_indexes(table_name, schema) if i.is_primary),
            None,
        )

    def list_foreign_keys(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ForeignKeyInfo]:
        """List all foreign keys of the given table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_foreign_key_sql(table_name, schema)
        result = self._parse_foreign_keys(
            self._executor.execute(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Return information for a specific foreign key, or None if not found."""
        return next(
            (fk for fk in self.list_foreign_keys(table_name, schema) if fk.name == fk_name),
            None,
        )

    def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """List all views in the database."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.VIEW, schema=schema, extra=str(include_system)
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_view_list_sql(schema, include_system)
        result = self._parse_views(self._executor.execute(sql, params), target)
        self._set_cached(key, result)
        return result

    def get_view_info(
        self, view_name: str, schema: Optional[str] = None
    ) -> Optional[ViewInfo]:
        """Return detailed information for a specific view, or None if not found."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_view_info_sql(view_name, schema)
        result = self._parse_view_info(self._executor.execute(sql, params), view_name, target)
        if result is not None:
            self._set_cached(key, result)
        return result

    def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named view exists."""
        return self.get_view_info(view_name, schema) is not None

    def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """List all triggers, optionally filtered by table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.TRIGGER, table_name or "*", schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_trigger_list_sql(table_name, schema)
        result = self._parse_triggers(self._executor.execute(sql, params), target)
        self._set_cached(key, result)
        return result

    def get_trigger_info(
        self, trigger_name: str, schema: Optional[str] = None
    ) -> Optional[TriggerInfo]:
        """Return information for a specific trigger, or None if not found."""
        return next(
            (t for t in self.list_triggers(schema=schema) if t.name == trigger_name),
            None,
        )


class AsyncAbstractIntrospector(IntrospectorMixin, ABC):
    """Abstract base class for asynchronous database introspectors.

    This class provides all asynchronous I/O methods for database introspection.
    Subclasses must implement all _parse_* methods.

    Public API (all methods are async, names match sync version):
        get_database_info(), list_tables(), get_table_info(), table_exists(),
        list_columns(), get_column_info(), column_exists(), list_indexes(),
        get_index_info(), get_primary_key(), list_foreign_keys(),
        get_foreign_key_info(), list_views(), get_view_info(), view_exists(),
        list_triggers(), get_trigger_info()

        Cache (synchronous): invalidate_cache(), clear_cache()
    """

    def __init__(self, backend: Any, executor: "AsyncIntrospectorExecutor") -> None:
        self._backend = backend
        self._executor = executor
        self._init_introspector_state()

    # ------------------------------------------------------------------ #
    # Public asynchronous API
    # Method names match the sync version (no _async suffix).
    # ------------------------------------------------------------------ #

    async def get_database_info(self) -> DatabaseInfo:
        """Return basic information about the connected database."""
        key = self._make_cache_key(IntrospectionScope.DATABASE)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_database_info_sql()
        result = self._parse_database_info(
            await self._executor.execute(sql, params)
        )
        self._set_cached(key, result)
        return result

    async def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """List tables (and optionally views/system tables) in the database."""
        key = self._make_cache_key(
            IntrospectionScope.TABLE, schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_table_list_sql(schema, include_system, True, table_type)
        result = self._parse_tables(
            await self._executor.execute(sql, params), schema
        )
        self._set_cached(key, result)
        return result

    async def get_table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        """Return detailed information for a specific table, including columns,
        indexes, and foreign keys."""
        key = self._make_cache_key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._get_cached(key)
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
        self._set_cached(key, table)
        return table

    async def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named table exists."""
        return await self.get_table_info(table_name, schema) is not None

    async def list_columns(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnInfo]:
        """List all columns of the given table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_column_info_sql(table_name, schema)
        result = self._parse_columns(
            await self._executor.execute(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    async def get_column_info(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> Optional[ColumnInfo]:
        """Return information for a specific column, or None if not found."""
        return next(
            (
                c
                for c in await self.list_columns(table_name, schema)
                if c.name == column_name
            ),
            None,
        )

    async def column_exists(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> bool:
        """Return True if the named column exists in the given table."""
        return await self.get_column_info(table_name, column_name, schema) is not None

    async def list_indexes(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """List all indexes of the given table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_index_info_sql(table_name, schema)
        result = self._parse_indexes(
            await self._executor.execute(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    async def get_index_info(
        self, table_name: str, index_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Return information for a specific index, or None if not found."""
        return next(
            (
                i
                for i in await self.list_indexes(table_name, schema)
                if i.name == index_name
            ),
            None,
        )

    async def get_primary_key(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Return the primary key index for the given table, or None."""
        return next(
            (i for i in await self.list_indexes(table_name, schema) if i.is_primary),
            None,
        )

    async def list_foreign_keys(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ForeignKeyInfo]:
        """List all foreign keys of the given table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_foreign_key_sql(table_name, schema)
        result = self._parse_foreign_keys(
            await self._executor.execute(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    async def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Return information for a specific foreign key, or None if not found."""
        return next(
            (
                fk
                for fk in await self.list_foreign_keys(table_name, schema)
                if fk.name == fk_name
            ),
            None,
        )

    async def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """List all views in the database."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.VIEW, schema=schema, extra=str(include_system)
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_view_list_sql(schema, include_system)
        result = self._parse_views(
            await self._executor.execute(sql, params), target
        )
        self._set_cached(key, result)
        return result

    async def get_view_info(
        self, view_name: str, schema: Optional[str] = None
    ) -> Optional[ViewInfo]:
        """Return detailed information for a specific view, or None if not found."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_view_info_sql(view_name, schema)
        result = self._parse_view_info(
            await self._executor.execute(sql, params), view_name, target
        )
        if result is not None:
            self._set_cached(key, result)
        return result

    async def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Return True if the named view exists."""
        return await self.get_view_info(view_name, schema) is not None

    async def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """List all triggers, optionally filtered by table."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.TRIGGER, table_name or "*", schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_trigger_list_sql(table_name, schema)
        result = self._parse_triggers(
            await self._executor.execute(sql, params), target
        )
        self._set_cached(key, result)
        return result

    async def get_trigger_info(
        self, trigger_name: str, schema: Optional[str] = None
    ) -> Optional[TriggerInfo]:
        """Return information for a specific trigger, or None if not found."""
        return next(
            (
                t
                for t in await self.list_triggers(schema=schema)
                if t.name == trigger_name
            ),
            None,
        )
