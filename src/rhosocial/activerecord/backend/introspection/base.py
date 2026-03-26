# src/rhosocial/activerecord/backend/introspection/base.py
"""
Abstract introspector base class.

AbstractIntrospector is the central object for all database introspection.
It owns cache management, SQL generation (via Expression+Dialect), and
exposes a consistent sync + async public API.

Concrete subclasses override _parse_* methods to handle database-specific
result formats. They may also override _build_*_sql() when the default
Expression-based SQL generation is not suitable.

Design principles:
  - Introspector generates SQL but never executes it directly.
    Execution is delegated to an IntrospectorExecutor that wraps the backend.
  - _parse_* methods are pure functions (no I/O), so sync and async paths
    share identical parsing logic — only the execute call differs.
  - Database-specific sub-introspectors (e.g. .pragma, .show) are exposed
    as lazy properties on the concrete Introspector subclass.
  - Users may inject a custom Introspector via backend.set_introspector().
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
from .executor import IntrospectorExecutor

if TYPE_CHECKING:  # pragma: no cover
    from ..dialect.base import SQLDialectBase


class AbstractIntrospector(ABC):
    """Base class for all database introspectors.

    Subclasses must implement all _parse_* abstract methods.
    They may additionally override _build_*_sql() methods and expose
    database-specific sub-introspectors as properties.

    Public API:
        Synchronous:  get_database_info(), list_tables(), get_table_info(),
                      table_exists(), list_columns(), get_column_info(),
                      column_exists(), list_indexes(), get_index_info(),
                      get_primary_key(), list_foreign_keys(),
                      get_foreign_key_info(), list_views(), get_view_info(),
                      view_exists(), list_triggers(), get_trigger_info()

        Asynchronous: same names with _async suffix.

        Cache:        invalidate_cache(), clear_cache()
    """

    DEFAULT_CACHE_TTL: int = 300  # seconds

    def __init__(self, backend: Any, executor: IntrospectorExecutor) -> None:
        self._backend = backend
        self._executor = executor
        self._cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl: int = self.DEFAULT_CACHE_TTL

    # ------------------------------------------------------------------ #
    # Dialect shortcut
    # ------------------------------------------------------------------ #

    @property
    def dialect(self) -> "SQLDialectBase":
        return self._backend.dialect

    def _get_default_schema(self) -> str:
        """Return the default schema name for this database.

        Subclasses should override to return the database-specific default
        (e.g. ``"main"`` for SQLite, ``"public"`` for PostgreSQL).
        Returns an empty string by default so generic callers can still work.
        """
        return ""

    # ------------------------------------------------------------------ #
    # Cache management
    # ------------------------------------------------------------------ #

    def _get_cached(self, key: str) -> Optional[Any]:
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
        with self._cache_lock:
            self._cache[key] = (data, time.time())

    def _make_cache_key(
        self,
        scope: IntrospectionScope,
        *args: str,
        schema: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> str:
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
    # SQL generation — delegates to Expression + Dialect
    # Subclasses may override to use database-specific statements.
    # ------------------------------------------------------------------ #

    def _build_database_info_sql(self) -> Tuple[str, tuple]:
        from ..expression.introspection import DatabaseInfoExpression
        return DatabaseInfoExpression(self.dialect).to_sql()

    def _build_table_list_sql(
        self,
        schema: Optional[str],
        include_system: bool,
        include_views: bool = True,
        table_type: Optional[str] = None,
    ) -> Tuple[str, tuple]:
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
        from ..expression.introspection import ColumnInfoExpression
        expr = ColumnInfoExpression(self.dialect, table_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_index_info_sql(
        self, table_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        from ..expression.introspection import IndexInfoExpression
        expr = IndexInfoExpression(self.dialect, table_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_foreign_key_sql(
        self, table_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        from ..expression.introspection import ForeignKeyExpression
        expr = ForeignKeyExpression(self.dialect, table_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_view_list_sql(
        self, schema: Optional[str], include_system: bool
    ) -> Tuple[str, tuple]:
        from ..expression.introspection import ViewListExpression
        expr = ViewListExpression(self.dialect).include_system(include_system)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_view_info_sql(
        self, view_name: str, schema: Optional[str]
    ) -> Tuple[str, tuple]:
        from ..expression.introspection import ViewInfoExpression
        expr = ViewInfoExpression(self.dialect, view_name)
        if schema:
            expr = expr.schema(schema)
        return expr.to_sql()

    def _build_trigger_list_sql(
        self, table_name: Optional[str], schema: Optional[str]
    ) -> Tuple[str, tuple]:
        from ..expression.introspection import TriggerListExpression
        expr = TriggerListExpression(self.dialect)
        if schema:
            expr = expr.schema(schema)
        if table_name:
            expr = expr.for_table(table_name)
        return expr.to_sql()

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O, shared by sync and async paths
    # ------------------------------------------------------------------ #

    @abstractmethod
    def _parse_database_info(self, rows: List[Dict[str, Any]]) -> DatabaseInfo:
        ...

    @abstractmethod
    def _parse_tables(
        self, rows: List[Dict[str, Any]], schema: Optional[str]
    ) -> List[TableInfo]:
        ...

    @abstractmethod
    def _parse_columns(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[ColumnInfo]:
        ...

    @abstractmethod
    def _parse_indexes(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[IndexInfo]:
        ...

    @abstractmethod
    def _parse_foreign_keys(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[ForeignKeyInfo]:
        ...

    @abstractmethod
    def _parse_views(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[ViewInfo]:
        ...

    @abstractmethod
    def _parse_view_info(
        self, rows: List[Dict[str, Any]], view_name: str, schema: str
    ) -> Optional[ViewInfo]:
        ...

    @abstractmethod
    def _parse_triggers(
        self, rows: List[Dict[str, Any]], schema: str
    ) -> List[TriggerInfo]:
        ...

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

    # ------------------------------------------------------------------ #
    # Public asynchronous API  (_async suffix)
    # Only the execute call differs from the sync path; _parse_* is reused.
    # ------------------------------------------------------------------ #

    async def get_database_info_async(self) -> DatabaseInfo:
        """Async version of get_database_info()."""
        key = self._make_cache_key(IntrospectionScope.DATABASE)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_database_info_sql()
        result = self._parse_database_info(
            await self._executor.execute_async(sql, params)
        )
        self._set_cached(key, result)
        return result

    async def list_tables_async(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Async version of list_tables()."""
        key = self._make_cache_key(
            IntrospectionScope.TABLE, schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_table_list_sql(schema, include_system, True, table_type)
        result = self._parse_tables(
            await self._executor.execute_async(sql, params), schema
        )
        self._set_cached(key, result)
        return result

    async def get_table_info_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[TableInfo]:
        """Async version of get_table_info()."""
        key = self._make_cache_key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        table = next(
            (t for t in await self.list_tables_async(schema) if t.name == table_name),
            None,
        )
        if table is None:
            return None
        table.columns = await self.list_columns_async(table_name, schema)
        table.indexes = await self.list_indexes_async(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys_async(table_name, schema)
        self._set_cached(key, table)
        return table

    async def table_exists_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> bool:
        """Async version of table_exists()."""
        return await self.get_table_info_async(table_name, schema) is not None

    async def list_columns_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ColumnInfo]:
        """Async version of list_columns()."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_column_info_sql(table_name, schema)
        result = self._parse_columns(
            await self._executor.execute_async(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    async def get_column_info_async(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> Optional[ColumnInfo]:
        """Async version of get_column_info()."""
        return next(
            (
                c
                for c in await self.list_columns_async(table_name, schema)
                if c.name == column_name
            ),
            None,
        )

    async def column_exists_async(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> bool:
        """Async version of column_exists()."""
        return await self.get_column_info_async(table_name, column_name, schema) is not None

    async def list_indexes_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[IndexInfo]:
        """Async version of list_indexes()."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_index_info_sql(table_name, schema)
        result = self._parse_indexes(
            await self._executor.execute_async(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    async def get_index_info_async(
        self, table_name: str, index_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Async version of get_index_info()."""
        return next(
            (
                i
                for i in await self.list_indexes_async(table_name, schema)
                if i.name == index_name
            ),
            None,
        )

    async def get_primary_key_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Async version of get_primary_key()."""
        return next(
            (i for i in await self.list_indexes_async(table_name, schema) if i.is_primary),
            None,
        )

    async def list_foreign_keys_async(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[ForeignKeyInfo]:
        """Async version of list_foreign_keys()."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_foreign_key_sql(table_name, schema)
        result = self._parse_foreign_keys(
            await self._executor.execute_async(sql, params), table_name, target
        )
        self._set_cached(key, result)
        return result

    async def get_foreign_key_info_async(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Async version of get_foreign_key_info()."""
        return next(
            (
                fk
                for fk in await self.list_foreign_keys_async(table_name, schema)
                if fk.name == fk_name
            ),
            None,
        )

    async def list_views_async(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Async version of list_views()."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.VIEW, schema=schema, extra=str(include_system)
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_view_list_sql(schema, include_system)
        result = self._parse_views(
            await self._executor.execute_async(sql, params), target
        )
        self._set_cached(key, result)
        return result

    async def get_view_info_async(
        self, view_name: str, schema: Optional[str] = None
    ) -> Optional[ViewInfo]:
        """Async version of get_view_info()."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_view_info_sql(view_name, schema)
        result = self._parse_view_info(
            await self._executor.execute_async(sql, params), view_name, target
        )
        if result is not None:
            self._set_cached(key, result)
        return result

    async def view_exists_async(
        self, view_name: str, schema: Optional[str] = None
    ) -> bool:
        """Async version of view_exists()."""
        return await self.get_view_info_async(view_name, schema) is not None

    async def list_triggers_async(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Async version of list_triggers()."""
        target = schema if schema is not None else self._get_default_schema()
        key = self._make_cache_key(
            IntrospectionScope.TRIGGER, table_name or "*", schema=schema
        )
        cached = self._get_cached(key)
        if cached is not None:
            return cached
        sql, params = self._build_trigger_list_sql(table_name, schema)
        result = self._parse_triggers(
            await self._executor.execute_async(sql, params), target
        )
        self._set_cached(key, result)
        return result

    async def get_trigger_info_async(
        self, trigger_name: str, schema: Optional[str] = None
    ) -> Optional[TriggerInfo]:
        """Async version of get_trigger_info()."""
        return next(
            (
                t
                for t in await self.list_triggers_async(schema=schema)
                if t.name == trigger_name
            ),
            None,
        )
