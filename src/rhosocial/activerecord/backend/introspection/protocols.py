# src/rhosocial/activerecord/backend/introspection/protocols.py
"""
Database introspection protocol definitions.

This module provides protocol classes for database introspection support.
"""

from typing import Protocol, List, Optional, runtime_checkable
from .types import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    ForeignKeyInfo,
    ViewInfo,
    TriggerInfo,
)


@runtime_checkable
class BackendIntrospectionSupport(Protocol):
    """Protocol for backend introspection support."""

    def get_database_info(self, name: str) -> DatabaseInfo:
        """Get database information.

        Args:
            name: Database name.

        Returns:
            DatabaseInfo object with database metadata.
        """
        ...

    def get_tables(self, schema: Optional[str] = None) -> List[TableInfo]:
        """Get list of tables in a schema.

        Args:
            schema: Schema/database name (optional).

        Returns:
            List of TableInfo objects.
        """
        ...

    def get_table_info(self, name: str, schema: Optional[str] = None) -> TableInfo:
        """Get table information.

        Args:
            name: Table name.
            schema: Schema/database name (optional).

        Returns:
            TableInfo object with table metadata.
        """
        ...

    def get_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Get list of columns for a table.

        Args:
            table_name: Table name.
            schema: Schema/database name (optional).

        Returns:
            List of ColumnInfo objects.
        """
        ...

    def get_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Get list of indexes for a table.

        Args:
            table_name: Table name.
            schema: Schema/database name (optional).

        Returns:
            List of IndexInfo objects.
        """
        ...

    def get_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Get list of foreign keys for a table.

        Args:
            table_name: Table name.
            schema: Schema/database name (optional).

        Returns:
            List of ForeignKeyInfo objects.
        """
        ...

    def get_views(self, schema: Optional[str] = None) -> List[ViewInfo]:
        """Get list of views in a schema.

        Args:
            schema: Schema/database name (optional).

        Returns:
            List of ViewInfo objects.
        """
        ...

    def get_triggers(self, schema: Optional[str] = None) -> List[TriggerInfo]:
        """Get list of triggers in a schema.

        Args:
            schema: Schema/database name (optional).

        Returns:
            List of TriggerInfo objects.
        """
        ...


@runtime_checkable
class AsyncBackendIntrospectionSupport(Protocol):
    """Protocol for async backend introspection support."""

    async def get_database_info(self, name: str) -> DatabaseInfo:
        """Get database information asynchronously."""
        ...

    async def get_tables(self, schema: Optional[str] = None) -> List[TableInfo]:
        """Get list of tables in a schema asynchronously."""
        ...

    async def get_table_info(self, name: str, schema: Optional[str] = None) -> TableInfo:
        """Get table information asynchronously."""
        ...

    async def get_columns(self, table_name: str, schema: Optional[str] = None) -> List[ColumnInfo]:
        """Get list of columns for a table asynchronously."""
        ...

    async def get_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """Get list of indexes for a table asynchronously."""
        ...

    async def get_foreign_keys(self, table_name: str, schema: Optional[str] = None) -> List[ForeignKeyInfo]:
        """Get list of foreign keys for a table asynchronously."""
        ...

    async def get_views(self, schema: Optional[str] = None) -> List[ViewInfo]:
        """Get list of views in a schema asynchronously."""
        ...

    async def get_triggers(self, schema: Optional[str] = None) -> List[TriggerInfo]:
        """Get list of triggers in a schema asynchronously."""
        ...
