# src/rhosocial/activerecord/backend/introspection/protocols.py
"""
Backend introspection protocol definitions.

This module defines protocols that backends implement to provide
database introspection capabilities. Unlike dialect protocols which
only declare capabilities, backend protocols define the actual
introspection methods.
"""

from typing import List, Optional, Protocol, runtime_checkable

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


@runtime_checkable
class BackendIntrospectionSupport(Protocol):
    """
    Protocol for backend introspection support.

    This protocol defines methods that backends implement to provide
    database introspection. Backends implement these methods directly,
    accessing their own connection and configuration without needing
    an external backend parameter.

    The dialect layer only declares capabilities (supports_* methods),
    while the backend layer implements the actual introspection logic.
    """

    # ========== Database Information ==========

    def get_database_info(self) -> DatabaseInfo:
        """Get database basic information.

        Returns:
            DatabaseInfo: Database metadata.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    # ========== Table Introspection ==========

    def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """List all tables in the database.

        Args:
            schema: Optional schema name to filter tables.
            include_system: Whether to include system tables.
            table_type: Optional table type filter (e.g., 'BASE TABLE', 'VIEW').

        Returns:
            List of table information.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Get detailed information for a specific table.

        Args:
            table_name: Name of the table to introspect.
            schema: Optional schema name.

        Returns:
            Table information, or None if not found.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    def table_exists(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Check if a table exists.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.

        Returns:
            True if table exists, False otherwise.
        """
        ...  # pragma: no cover

    # ========== Column Introspection ==========

    def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """List all columns of a table.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.

        Returns:
            List of column information.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
            ObjectNotFoundError: If table does not exist.
        """
        ...  # pragma: no cover

    def get_column_info(self, table_name: str, column_name: str, schema: Optional[str] = None) -> Optional[ColumnInfo]:
        """Get detailed information for a specific column.

        Args:
            table_name: Name of the table.
            column_name: Name of the column.
            schema: Optional schema name.

        Returns:
            Column information, or None if not found.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
            ObjectNotFoundError: If table does not exist.
        """
        ...  # pragma: no cover

    def column_exists(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Check if a column exists in a table.

        Args:
            table_name: Name of the table.
            column_name: Name of the column.
            schema: Optional schema name.

        Returns:
            True if column exists, False otherwise.
        """
        ...  # pragma: no cover

    # ========== Index Introspection ==========

    def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of a table.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.

        Returns:
            List of index information.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
            ObjectNotFoundError: If table does not exist.
        """
        ...  # pragma: no cover

    def get_index_info(self, table_name: str, index_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Get detailed information for a specific index.

        Args:
            table_name: Name of the table.
            index_name: Name of the index.
            schema: Optional schema name.

        Returns:
            Index information, or None if not found.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
            ObjectNotFoundError: If table does not exist.
        """
        ...  # pragma: no cover

    def get_primary_key(self, table_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Get primary key information for a table.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.

        Returns:
            Primary key index information, or None if no primary key.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    # ========== Foreign Key Introspection ==========

    def list_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """List all foreign keys of a table.

        Args:
            table_name: Name of the table.
            schema: Optional schema name.

        Returns:
            List of foreign key information.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
            ObjectNotFoundError: If table does not exist.
        """
        ...  # pragma: no cover

    def get_foreign_key_info(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Get detailed information for a specific foreign key.

        Args:
            table_name: Name of the table.
            fk_name: Name of the foreign key constraint.
            schema: Optional schema name.

        Returns:
            Foreign key information, or None if not found.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
            ObjectNotFoundError: If table does not exist.
        """
        ...  # pragma: no cover

    # ========== View Introspection ==========

    def list_views(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """List all views in the database.

        Args:
            schema: Optional schema name to filter views.
            include_system: Whether to include system views.

        Returns:
            List of view information.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    def get_view_info(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Get detailed information for a specific view.

        Args:
            view_name: Name of the view.
            schema: Optional schema name.

        Returns:
            View information, or None if not found.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    def view_exists(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Check if a view exists.

        Args:
            view_name: Name of the view.
            schema: Optional schema name.

        Returns:
            True if view exists, False otherwise.
        """
        ...  # pragma: no cover

    # ========== Trigger Introspection ==========

    def list_triggers(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """List all triggers (optionally filtered by table).

        Args:
            table_name: Optional table name to filter triggers.
            schema: Optional schema name.

        Returns:
            List of trigger information.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    def get_trigger_info(self, trigger_name: str, schema: Optional[str] = None) -> Optional[TriggerInfo]:
        """Get detailed information for a specific trigger.

        Args:
            trigger_name: Name of the trigger.
            schema: Optional schema name.

        Returns:
            Trigger information, or None if not found.

        Raises:
            IntrospectionNotSupportedError: If not supported by backend.
            IntrospectionQueryError: If query execution fails.
        """
        ...  # pragma: no cover

    # ========== Cache Management ==========

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
        ...  # pragma: no cover

    def clear_introspection_cache(self) -> None:
        """Clear all introspection cache."""
        ...  # pragma: no cover


@runtime_checkable
class AsyncBackendIntrospectionSupport(Protocol):
    """
    Protocol for async backend introspection support.

    Async version of BackendIntrospectionSupport with symmetric API.
    """

    # ========== Database Information ==========

    async def get_database_info_async(self) -> DatabaseInfo:
        """Async get database basic information."""
        ...  # pragma: no cover

    # ========== Table Introspection ==========

    async def list_tables_async(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[TableInfo]:
        """Async list all tables in the database."""
        ...  # pragma: no cover

    async def get_table_info_async(self, table_name: str, schema: Optional[str] = None) -> Optional[TableInfo]:
        """Async get detailed information for a specific table."""
        ...  # pragma: no cover

    async def table_exists_async(self, table_name: str, schema: Optional[str] = None) -> bool:
        """Async check if a table exists."""
        ...  # pragma: no cover

    # ========== Column Introspection ==========

    async def list_columns_async(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Async list all columns of a table."""
        ...  # pragma: no cover

    async def get_column_info_async(
        self, table_name: str, column_name: str, schema: Optional[str] = None
    ) -> Optional[ColumnInfo]:
        """Async get detailed information for a specific column."""
        ...  # pragma: no cover

    async def column_exists_async(self, table_name: str, column_name: str, schema: Optional[str] = None) -> bool:
        """Async check if a column exists in a table."""
        ...  # pragma: no cover

    # ========== Index Introspection ==========

    async def list_indexes_async(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Async list all indexes of a table."""
        ...  # pragma: no cover

    async def get_index_info_async(
        self, table_name: str, index_name: str, schema: Optional[str] = None
    ) -> Optional[IndexInfo]:
        """Async get detailed information for a specific index."""
        ...  # pragma: no cover

    async def get_primary_key_async(self, table_name: str, schema: Optional[str] = None) -> Optional[IndexInfo]:
        """Async get primary key information for a table."""
        ...  # pragma: no cover

    # ========== Foreign Key Introspection ==========

    async def list_foreign_keys_async(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Async list all foreign keys of a table."""
        ...  # pragma: no cover

    async def get_foreign_key_info_async(
        self, table_name: str, fk_name: str, schema: Optional[str] = None
    ) -> Optional[ForeignKeyInfo]:
        """Async get detailed information for a specific foreign key."""
        ...  # pragma: no cover

    # ========== View Introspection ==========

    async def list_views_async(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> List[ViewInfo]:
        """Async list all views in the database."""
        ...  # pragma: no cover

    async def get_view_info_async(self, view_name: str, schema: Optional[str] = None) -> Optional[ViewInfo]:
        """Async get detailed information for a specific view."""
        ...  # pragma: no cover

    async def view_exists_async(self, view_name: str, schema: Optional[str] = None) -> bool:
        """Async check if a view exists."""
        ...  # pragma: no cover

    # ========== Trigger Introspection ==========

    async def list_triggers_async(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[TriggerInfo]:
        """Async list all triggers (optionally filtered by table)."""
        ...  # pragma: no cover

    async def get_trigger_info_async(self, trigger_name: str, schema: Optional[str] = None) -> Optional[TriggerInfo]:
        """Async get detailed information for a specific trigger."""
        ...  # pragma: no cover

    # ========== Cache Management ==========

    async def invalidate_introspection_cache_async(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Async invalidate introspection cache."""
        ...  # pragma: no cover

    async def clear_introspection_cache_async(self) -> None:
        """Async clear all introspection cache."""
        ...  # pragma: no cover
