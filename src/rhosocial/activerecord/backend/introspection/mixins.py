# src/rhosocial/activerecord/backend/introspection/mixins.py
"""
Backend introspection mixin implementations.

This module provides mixin classes that backends can inherit to gain
introspection capabilities. The mixins provide common functionality
like caching, while backends implement the actual introspection queries.
"""

import threading
import time
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    pass

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
from .errors import (
    IntrospectionNotSupportedError,
)


class IntrospectionMixin:
    """
    Mixin providing database introspection capabilities for backends.

    This mixin provides:
    - Cache management for introspection results
    - Common utility methods (exists checks)
    - Abstract methods for backends to implement
    - **NEW: Prerequisites checking**

    Backends inheriting this mixin must implement the _query_* methods
    to perform actual database introspection queries.

    The mixin accesses backend's connection and configuration directly
    through 'self', without needing an external backend parameter.
    """

    # Default cache TTL in seconds (5 minutes)
    DEFAULT_CACHE_TTL: int = 300

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._introspection_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = self.DEFAULT_CACHE_TTL

    # ========== NEW: Prerequisites Check ==========

    def _check_introspection_prerequisites(self) -> None:
        """Check prerequisites for introspection methods.

        This method verifies:
        - Connection is established
        - Dialect is initialized
        - Dialect implements IntrospectionSupport protocol
        - Dialect declares introspection support

        Raises:
            IntrospectionNotSupportedError: If prerequisites not met.
        """
        # Check connection
        if not getattr(self, "_connection", None):
            raise IntrospectionNotSupportedError(
                "Cannot perform introspection: no database connection. Call connect() first."
            )
        # Check dialect exists
        dialect = getattr(self, "_dialect", None)
        if dialect is None:
            raise IntrospectionNotSupportedError("Cannot perform introspection: dialect not initialized.")
        # Check dialect implements IntrospectionSupport protocol
        from ..dialect.protocols import IntrospectionSupport

        if not isinstance(dialect, IntrospectionSupport):
            raise IntrospectionNotSupportedError("Introspection is not supported by this backend dialect.")
        # Check dialect declares introspection support
        if not dialect.supports_introspection():
            raise IntrospectionNotSupportedError("Introspection is not supported by this backend dialect.")

    # ========== Cache Management ==========

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached introspection result.

        Args:
            key: Cache key.

        Returns:
            Cached data if valid, None if expired or not found.
        """
        with self._cache_lock:
            entry = self._introspection_cache.get(key)
            if entry is None:
                return None
            data, timestamp = entry
            if time.time() - timestamp > self._cache_ttl:
                # Cache expired
                del self._introspection_cache[key]
                return None
            return data

    def _set_cached(self, key: str, data: Any) -> None:
        """Cache introspection result.

        Args:
            key: Cache key.
            data: Data to cache.
        """
        with self._cache_lock:
            self._introspection_cache[key] = (data, time.time())

    def _make_cache_key(
        self,
        scope: IntrospectionScope,
        *args: str,
        schema: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> str:
        """Generate cache key.

        Args:
            scope: Introspection scope.
            *args: Additional key components.
            schema: Optional schema name.
            extra: Optional extra component.

        Returns:
            Cache key string.
        """
        parts = [scope.value]
        if schema:
            parts.append(f"schema:{schema}")
        parts.extend(args)
        if extra:
            parts.append(extra)
        return ":".join(parts)

    def invalidate_introspection_cache(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Invalidate introspection cache.

        Args:
            scope: Optional scope to invalidate (None = all).
            name: Optional object name within scope.
        """
        with self._cache_lock:
            if scope is None:
                # Clear all cache
                self._introspection_cache.clear()
            elif name is None:
                # Clear all entries for scope
                prefix = f"{scope.value}:"
                keys_to_delete = [k for k in self._introspection_cache if k.startswith(prefix)]
                for key in keys_to_delete:
                    del self._introspection_cache[key]
            else:
                # Clear specific entry (need to find matching keys)
                prefix = f"{scope.value}:"
                keys_to_delete = [k for k in self._introspection_cache if k.startswith(prefix) and name in k]
                for key in keys_to_delete:
                    del self._introspection_cache[key]

    def clear_introspection_cache(self) -> None:
        """Clear all introspection cache."""
        with self._cache_lock:
            self._introspection_cache.clear()

    # ========== Abstract Query Methods ==========

    @abstractmethod
    def _query_database_info(self) -> DatabaseInfo:
        """Query database information.

        Returns:
            Database metadata.

        Raises:
            IntrospectionNotSupportedError: If not supported.
            IntrospectionQueryError: If query fails.
        """
        ...

    @abstractmethod
    def _query_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Query table list.

        Args:
            schema: Optional schema filter.
            include_system: Whether to include system tables.
            table_type: Optional table type filter.

        Returns:
            List of table information.
        """
        ...

    @abstractmethod
    def _query_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Query table information.

        Args:
            table_name: Table name.
            schema: Optional schema name.

        Returns:
            Table information or None if not found.
        """
        ...

    @abstractmethod
    def _query_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Query column list for a table.

        Args:
            table_name: Table name.
            schema: Optional schema name.

        Returns:
            List of column information.
        """
        ...

    @abstractmethod
    def _query_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Query index list for a table.

        Args:
            table_name: Table name.
            schema: Optional schema name.

        Returns:
            List of index information.
        """
        ...

    @abstractmethod
    def _query_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Query foreign key list for a table.

        Args:
            table_name: Table name.
            schema: Optional schema name.

        Returns:
            List of foreign key information.
        """
        ...

    @abstractmethod
    def _query_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Query view list.

        Args:
            schema: Optional schema filter.
            include_system: Whether to include system views.

        Returns:
            List of view information.
        """
        ...

    @abstractmethod
    def _query_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Query view information.

        Args:
            view_name: View name.
            schema: Optional schema name.

        Returns:
            View information or None if not found.
        """
        ...

    @abstractmethod
    def _query_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Query trigger list.

        Args:
            table_name: Optional table filter.
            schema: Optional schema name.

        Returns:
            List of trigger information.
        """
        ...

    # ========== Public Introspection Methods ==========

    def get_database_info(self) -> DatabaseInfo:
        """Get database basic information."""
        cache_key = self._make_cache_key(IntrospectionScope.DATABASE)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_database_info()
        self._set_cached(cache_key, result)
        return result

    def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """List all tables in the database."""
        cache_key = self._make_cache_key(IntrospectionScope.TABLE, schema=schema, extra=str(include_system))
        if table_type:
            cache_key += f":type:{table_type}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_tables(schema, include_system, table_type)
        self._set_cached(cache_key, result)
        return result

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Get detailed information for a specific table."""
        cache_key = self._make_cache_key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_table_info(table_name, schema)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if a table exists."""
        return self.get_table_info(table_name, schema) is not None

    def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """List all columns of a table."""
        cache_key = self._make_cache_key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_columns(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    def get_column_info(self, table_name: str, column_name: str, schema: Optional[str] = None) -> Optional[ColumnInfo]:
        """Get detailed information for a specific column."""
        columns = self.list_columns(table_name, schema)
        for col in columns:
            if col.name == column_name:
                return col
        return None

    def column_exists(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Check if a column exists in a table."""
        return self.get_column_info(table_name, column_name, schema) is not None

    def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of a table."""
        cache_key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_indexes(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    def get_index_info(self, table_name: str, index_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Get detailed information for a specific index."""
        indexes = self.list_indexes(table_name, schema)
        for idx in indexes:
            if idx.name == index_name:
                return idx
        return None

    def get_primary_key(self, table_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Get primary key information for a table."""
        indexes = self.list_indexes(table_name, schema)
        for idx in indexes:
            if idx.is_primary:
                return idx
        return None

    def list_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """List all foreign keys of a table."""
        cache_key = self._make_cache_key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_foreign_keys(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Get detailed information for a specific foreign key."""
        fks = self.list_foreign_keys(table_name, schema)
        for fk in fks:
            if fk.name == fk_name:
                return fk
        return None

    def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """List all views in the database."""
        cache_key = self._make_cache_key(IntrospectionScope.VIEW, schema=schema, extra=str(include_system))
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_views(schema, include_system)
        self._set_cached(cache_key, result)
        return result

    def get_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Get detailed information for a specific view."""
        cache_key = self._make_cache_key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_view_info(view_name, schema)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Check if a view exists."""
        return self.get_view_info(view_name, schema) is not None

    def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """List all triggers (optionally filtered by table)."""
        cache_key = self._make_cache_key(IntrospectionScope.TRIGGER, table_name or "*", schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = self._query_triggers(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    def get_trigger_info(self, trigger_name: str, schema: Optional[str] = None) -> Optional[TriggerInfo]:
        """Get detailed information for a specific trigger."""
        triggers = self.list_triggers(schema=schema)
        for trig in triggers:
            if trig.name == trigger_name:
                return trig
        return None


class AsyncIntrospectionMixin:
    """
    Async mixin providing database introspection capabilities for backends.

    Async version of IntrospectionMixin with symmetric API.
    """

    # Default cache TTL in seconds (5 minutes)
    DEFAULT_CACHE_TTL: int = 300

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._introspection_cache: Dict[str, Tuple[Any, float]] = {}
        self._cache_lock = threading.RLock()
        self._cache_ttl = self.DEFAULT_CACHE_TTL

    # ========== Cache Management ==========

    def _get_cached(self, key: str) -> Optional[Any]:
        """Get cached introspection result."""
        with self._cache_lock:
            entry = self._introspection_cache.get(key)
            if entry is None:
                return None
            data, timestamp = entry
            if time.time() - timestamp > self._cache_ttl:
                del self._introspection_cache[key]
                return None
            return data

    def _set_cached(self, key: str, data: Any) -> None:
        """Cache introspection result."""
        with self._cache_lock:
            self._introspection_cache[key] = (data, time.time())

    def _make_cache_key(
        self,
        scope: IntrospectionScope,
        *args: str,
        schema: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> str:
        """Generate cache key."""
        parts = [scope.value]
        if schema:
            parts.append(f"schema:{schema}")
        parts.extend(args)
        if extra:
            parts.append(extra)
        return ":".join(parts)

    async def invalidate_introspection_cache(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Invalidate introspection cache asynchronously."""
        with self._cache_lock:
            if scope is None:
                self._introspection_cache.clear()
            elif name is None:
                prefix = f"{scope.value}:"
                keys_to_delete = [k for k in self._introspection_cache if k.startswith(prefix)]
                for key in keys_to_delete:
                    del self._introspection_cache[key]
            else:
                prefix = f"{scope.value}:"
                keys_to_delete = [k for k in self._introspection_cache if k.startswith(prefix) and name in k]
                for key in keys_to_delete:
                    del self._introspection_cache[key]

    async def clear_introspection_cache(self) -> None:
        """Clear all introspection cache asynchronously."""
        with self._cache_lock:
            self._introspection_cache.clear()

    # ========== Abstract Query Methods ==========

    @abstractmethod
    async def _query_database_info(self) -> DatabaseInfo:
        """Query database information asynchronously."""
        ...

    @abstractmethod
    async def _query_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Query table list asynchronously."""
        ...

    @abstractmethod
    async def _query_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Query table information asynchronously."""
        ...

    @abstractmethod
    async def _query_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Query column list for a table asynchronously."""
        ...

    @abstractmethod
    async def _query_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Query index list for a table asynchronously."""
        ...

    @abstractmethod
    async def _query_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Query foreign key list for a table asynchronously."""
        ...

    @abstractmethod
    async def _query_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Query view list asynchronously."""
        ...

    @abstractmethod
    async def _query_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Query view information asynchronously."""
        ...

    @abstractmethod
    async def _query_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Query trigger list asynchronously."""
        ...

    # ========== Public Introspection Methods ==========

    async def get_database_info(self) -> DatabaseInfo:
        """Get database basic information asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.DATABASE)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_database_info()
        self._set_cached(cache_key, result)
        return result

    async def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """List all tables in the database asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.TABLE, schema=schema, extra=str(include_system))
        if table_type:
            cache_key += f":type:{table_type}"

        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_tables(schema, include_system, table_type)
        self._set_cached(cache_key, result)
        return result

    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Get detailed information for a specific table asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_table_info(table_name, schema)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    async def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if a table exists asynchronously."""
        return await self.get_table_info(table_name, schema) is not None

    async def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """List all columns of a table asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_columns(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    async def get_column_info(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> Optional[ColumnInfo]:
        """Get detailed information for a specific column asynchronously."""
        columns = await self.list_columns(table_name, schema)
        for col in columns:
            if col.name == column_name:
                return col
        return None

    async def column_exists(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Check if a column exists in a table asynchronously."""
        return await self.get_column_info(table_name, column_name, schema) is not None

    async def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of a table asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_indexes(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    async def get_index_info(
        self, table_name: str, index_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Get detailed information for a specific index asynchronously."""
        indexes = await self.list_indexes(table_name, schema)
        for idx in indexes:
            if idx.name == index_name:
                return idx
        return None

    async def get_primary_key(self, table_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Get primary key information for a table asynchronously."""
        indexes = await self.list_indexes(table_name, schema)
        for idx in indexes:
            if idx.is_primary:
                return idx
        return None

    async def list_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """List all foreign keys of a table asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.FOREIGN_KEY, table_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_foreign_keys(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    async def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Get detailed information for a specific foreign key asynchronously."""
        fks = await self.list_foreign_keys(table_name, schema)
        for fk in fks:
            if fk.name == fk_name:
                return fk
        return None

    async def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """List all views in the database asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.VIEW, schema=schema, extra=str(include_system))
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_views(schema, include_system)
        self._set_cached(cache_key, result)
        return result

    async def get_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Get detailed information for a specific view asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.VIEW, view_name, schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_view_info(view_name, schema)
        if result is not None:
            self._set_cached(cache_key, result)
        return result

    async def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Check if a view exists asynchronously."""
        return await self.get_view_info(view_name, schema) is not None

    async def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """List all triggers (optionally filtered by table) asynchronously."""
        cache_key = self._make_cache_key(IntrospectionScope.TRIGGER, table_name or "*", schema=schema)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached  # type: ignore

        result = await self._query_triggers(table_name, schema)
        self._set_cached(cache_key, result)
        return result

    async def get_trigger_info(self, trigger_name: str, schema: Optional[str] = None) -> Optional[TriggerInfo]:
        """Get detailed information for a specific trigger asynchronously."""
        triggers = await self.list_triggers(schema=schema)
        for trig in triggers:
            if trig.name == trigger_name:
                return trig
        return None
