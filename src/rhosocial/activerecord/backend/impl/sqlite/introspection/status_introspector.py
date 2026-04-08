# src/rhosocial/activerecord/backend/impl/sqlite/introspection/status_introspector.py
"""
SQLite server status introspector.

SQLite is an embedded database without a traditional server concept.
This module provides status introspection by reading PRAGMA values
and database file information.

Design principle: Sync and Async are separate and cannot coexist.
- SyncSQLiteStatusIntrospector: for synchronous backends
- AsyncSQLiteStatusIntrospector: for asynchronous backends
"""

import os
import sqlite3
from typing import Any, Dict, List, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.introspection.status import (
    StatusItem,
    StatusCategory,
    ServerOverview,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
    SessionInfo,
    SyncAbstractStatusIntrospector,
    AsyncAbstractStatusIntrospector,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..backend import SQLiteBackend
    from ..async_backend import AsyncSQLiteBackend


# SQLite PRAGMA parameters to expose as status items
# Format: (pragma_name, category, description, unit, is_readonly)
SQLITE_PRAGMA_CONFIG = [
    # Configuration
    ("journal_mode", StatusCategory.CONFIGURATION, "Write-ahead logging mode", None, False),
    ("synchronous", StatusCategory.CONFIGURATION, "Synchronization mode", None, False),
    ("foreign_keys", StatusCategory.CONFIGURATION, "Foreign key constraint enforcement", None, False),
    ("temp_store", StatusCategory.CONFIGURATION, "Temporary storage location", None, False),
    ("encoding", StatusCategory.CONFIGURATION, "Database text encoding", None, True),
    ("page_size", StatusCategory.STORAGE, "Database page size", "bytes", True),
    ("cache_size", StatusCategory.PERFORMANCE, "Number of pages in cache", "pages", False),
    ("cache_spill", StatusCategory.PERFORMANCE, "Cache spill prevention", "bytes", False),
    ("busy_timeout", StatusCategory.CONFIGURATION, "Busy timeout", "milliseconds", False),
    ("lock_timeout", StatusCategory.CONFIGURATION, "Lock timeout", "milliseconds", False),
    ("wal_autocheckpoint", StatusCategory.PERFORMANCE, "WAL auto-checkpoint interval", "pages", False),
    ("automatic_index", StatusCategory.PERFORMANCE, "Automatic index creation", None, False),
    ("recursive_triggers", StatusCategory.CONFIGURATION, "Recursive trigger support", None, False),
    ("secure_delete", StatusCategory.SECURITY, "Secure delete mode", None, False),
    ("ignore_check_constraints", StatusCategory.CONFIGURATION, "Ignore CHECK constraints", None, False),
    ("defer_foreign_keys", StatusCategory.CONFIGURATION, "Deferred foreign key constraints", None, False),
    ("legacy_alter_table", StatusCategory.CONFIGURATION, "Legacy ALTER TABLE behavior", None, False),
    ("query_only", StatusCategory.SECURITY, "Read-only mode", None, False),
    ("reverse_unordered_selects", StatusCategory.PERFORMANCE, "Reverse unordered SELECTs", None, False),
    ("trusted_schema", StatusCategory.SECURITY, "Trust schema for DML statements", None, False),
]


class SQLiteStatusIntrospectorMixin:
    """Mixin providing shared logic for SQLite status introspectors.

    Both SyncSQLiteStatusIntrospector and AsyncSQLiteStatusIntrospector
    inherit from this mixin to share non-I/O logic.
    """

    def _get_vendor_name(self) -> str:
        """Get SQLite vendor name."""
        return "SQLite"

    def _parse_pragma_value(self, value: Any) -> Any:
        """Parse PRAGMA value to appropriate Python type.

        Args:
            value: Raw PRAGMA value

        Returns:
            Parsed value (int, str, or original value)
        """
        if isinstance(value, int):
            return value
        if isinstance(value, str):
            # Try to parse as integer
            try:
                return int(value)
            except ValueError:
                return value
        return value

    def _create_status_item(
        self,
        name: str,
        value: Any,
        category: StatusCategory,
        description: Optional[str] = None,
        unit: Optional[str] = None,
        is_readonly: bool = False,
    ) -> StatusItem:
        """Create a StatusItem with parsed value.

        Args:
            name: Parameter name
            value: Raw value from PRAGMA
            category: Status category
            description: Human-readable description
            unit: Unit of measurement
            is_readonly: Whether parameter is read-only

        Returns:
            StatusItem object
        """
        return StatusItem(
            name=name,
            value=self._parse_pragma_value(value),
            category=category,
            description=description,
            unit=unit,
            is_readonly=is_readonly,
        )

    def _get_database_file_info(self, db_path: str) -> Dict[str, Any]:
        """Get information about the database file.

        Args:
            db_path: Path to database file or ":memory:"

        Returns:
            Dictionary with file information
        """
        info: Dict[str, Any] = {
            "is_memory": db_path == ":memory:",
            "path": db_path,
        }

        if db_path != ":memory:":
            try:
                stat = os.stat(db_path)
                info["size_bytes"] = stat.st_size
                info["mtime"] = stat.st_mtime
            except OSError:
                pass

        return info

    def _build_server_overview(
        self,
        configuration: List[StatusItem],
        performance: List[StatusItem],
        storage: StorageInfo,
        databases: List[DatabaseBriefInfo],
        version: str,
    ) -> ServerOverview:
        """Build ServerOverview from collected data.

        Args:
            configuration: Configuration parameters
            performance: Performance metrics
            storage: Storage information
            databases: Database list
            version: SQLite version string

        Returns:
            ServerOverview object
        """
        return ServerOverview(
            server_version=version,
            server_vendor=self._get_vendor_name(),
            configuration=configuration,
            performance=performance,
            connections=ConnectionInfo(),  # SQLite has no connection concept
            storage=storage,
            databases=databases,
            users=[],  # SQLite has no user concept
            extra={
                "sqlite_version": sqlite3.sqlite_version,
                "sqlite_version_info": sqlite3.sqlite_version_info,
            },
        )


class SyncSQLiteStatusIntrospector(
    SQLiteStatusIntrospectorMixin, SyncAbstractStatusIntrospector
):
    """Synchronous SQLite status introspector.

    Reads PRAGMA values and database file information to provide
    a status overview of the SQLite database.

    Usage::

        backend = SQLiteBackend(connection_config=config)
        backend.connect()
        status = backend.introspector.status.get_overview()
        print(status.server_version)
    """

    def __init__(self, backend: "SQLiteBackend") -> None:
        super().__init__(backend)
        self._pragma = backend.introspector.pragma

    def get_overview(self) -> ServerOverview:
        """Get complete SQLite status overview.

        Returns:
            ServerOverview with PRAGMA configuration and file info
        """
        configuration = self.list_configuration()
        performance = self.list_performance_metrics()
        storage = self.get_storage_info()
        databases = self.list_databases()

        version = ".".join(map(str, self._backend.dialect.version))

        return self._build_server_overview(
            configuration=configuration,
            performance=performance,
            storage=storage,
            databases=databases,
            version=version,
        )

    def list_configuration(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List SQLite configuration parameters via PRAGMA.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects
        """
        items = []

        for pragma_name, pragma_category, description, unit, is_readonly in SQLITE_PRAGMA_CONFIG:
            if category and pragma_category != category:
                continue

            try:
                value = self._pragma.get(pragma_name)
                if value is not None:
                    # Extract value from dict if needed
                    if isinstance(value, dict):
                        value = list(value.values())[0] if value else None

                    item = self._create_status_item(
                        name=pragma_name,
                        value=value,
                        category=pragma_category,
                        description=description,
                        unit=unit,
                        is_readonly=is_readonly,
                    )
                    items.append(item)
            except Exception:
                # Skip PRAGMA that failed to read
                pass

        return items

    def list_performance_metrics(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List SQLite performance metrics.

        Note: SQLite doesn't have many built-in performance metrics.
        Most performance-related values are configuration parameters.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects
        """
        # Performance metrics are included in configuration
        # Filter by PERFORMANCE category
        return self.list_configuration(category=StatusCategory.PERFORMANCE)

    def get_connection_info(self) -> ConnectionInfo:
        """Get connection information.

        SQLite doesn't have server connections, so this returns empty info.

        Returns:
            Empty ConnectionInfo
        """
        return ConnectionInfo()

    def get_session_info(self) -> SessionInfo:
        """Get current session/connection information.

        SQLite doesn't have sessions, so this returns empty info.

        Returns:
            Empty SessionInfo
        """
        return SessionInfo()

    def get_storage_info(self) -> StorageInfo:
        """Get storage information.

        Returns:
            StorageInfo with database file size
        """
        storage = StorageInfo()

        # Get database file path
        db_path = self._backend.config.database

        if db_path == ":memory:":
            storage.total_size_bytes = 0
            storage.extra["is_memory"] = True
        else:
            file_info = self._get_database_file_info(db_path)
            storage.total_size_bytes = file_info.get("size_bytes")
            storage.extra["path"] = db_path
            storage.extra["is_memory"] = False

        # Get page count for more accurate size
        try:
            page_count = self._pragma.get("page_count")
            if page_count and isinstance(page_count, dict):
                page_count = list(page_count.values())[0] if page_count else None

            page_size = self._pragma.get("page_size")
            if page_size and isinstance(page_size, dict):
                page_size = list(page_size.values())[0] if page_size else None

            if page_count and page_size:
                calculated_size = int(page_count) * int(page_size)
                storage.data_size_bytes = calculated_size
                if storage.total_size_bytes is None:
                    storage.total_size_bytes = calculated_size
        except Exception:
            pass

        return storage

    def list_databases(self) -> List[DatabaseBriefInfo]:
        """List attached databases.

        SQLite can have multiple attached databases via ATTACH command.

        Returns:
            List of DatabaseBriefInfo objects (main + attached databases)
        """
        databases = []

        # Get main database
        db_path = self._backend.config.database
        main_db = DatabaseBriefInfo(
            name="main",
            schema=None,
            extra={"path": db_path, "is_memory": db_path == ":memory:"},
        )

        # Get table count for main database
        try:
            tables = self._backend.introspector.list_tables(include_system=False)
            main_db.table_count = len(tables)
        except Exception:
            pass

        databases.append(main_db)

        # Get attached databases
        try:
            pragma_databases = self._pragma.execute("database_list")
            for row in pragma_databases:
                # database_list returns: seq, name, file
                name = row.get("name")
                if name and name != "main":
                    db_info = DatabaseBriefInfo(
                        name=name,
                        schema=None,
                        extra={"path": row.get("file", "")},
                    )
                    databases.append(db_info)
        except Exception:
            pass

        return databases

    def list_users(self) -> List[UserInfo]:
        """List users.

        SQLite has no user management, so this returns empty list.

        Returns:
            Empty list
        """
        return []


class AsyncSQLiteStatusIntrospector(
    SQLiteStatusIntrospectorMixin, AsyncAbstractStatusIntrospector
):
    """Asynchronous SQLite status introspector.

    Reads PRAGMA values and database file information to provide
    a status overview of the SQLite database.

    Usage::

        backend = AsyncSQLiteBackend(connection_config=config)
        await backend.connect()
        status = await backend.introspector.status.get_overview()
        print(status.server_version)
    """

    def __init__(self, backend: "AsyncSQLiteBackend") -> None:
        super().__init__(backend)
        self._pragma = backend.introspector.pragma

    async def get_overview(self) -> ServerOverview:
        """Get complete SQLite status overview.

        Returns:
            ServerOverview with PRAGMA configuration and file info
        """
        configuration = await self.list_configuration()
        performance = await self.list_performance_metrics()
        storage = await self.get_storage_info()
        databases = await self.list_databases()

        version = ".".join(map(str, self._backend.dialect.version))

        return self._build_server_overview(
            configuration=configuration,
            performance=performance,
            storage=storage,
            databases=databases,
            version=version,
        )

    async def list_configuration(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List SQLite configuration parameters via PRAGMA.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects
        """
        items = []

        for pragma_name, pragma_category, description, unit, is_readonly in SQLITE_PRAGMA_CONFIG:
            if category and pragma_category != category:
                continue

            try:
                value = await self._pragma.get(pragma_name)
                if value is not None:
                    # Extract value from dict if needed
                    if isinstance(value, dict):
                        value = list(value.values())[0] if value else None

                    item = self._create_status_item(
                        name=pragma_name,
                        value=value,
                        category=pragma_category,
                        description=description,
                        unit=unit,
                        is_readonly=is_readonly,
                    )
                    items.append(item)
            except Exception:
                # Skip PRAGMA that failed to read
                pass

        return items

    async def list_performance_metrics(
        self, category: Optional[StatusCategory] = None
    ) -> List[StatusItem]:
        """List SQLite performance metrics.

        Args:
            category: Optional category filter

        Returns:
            List of StatusItem objects
        """
        return await self.list_configuration(category=StatusCategory.PERFORMANCE)

    async def get_connection_info(self) -> ConnectionInfo:
        """Get connection information (empty for SQLite).

        Returns:
            Empty ConnectionInfo
        """
        return ConnectionInfo()

    async def get_session_info(self) -> SessionInfo:
        """Get current session/connection information (empty for SQLite).

        Returns:
            Empty SessionInfo
        """
        return SessionInfo()

    async def get_storage_info(self) -> StorageInfo:
        """Get storage information.

        Returns:
            StorageInfo with database file size
        """
        storage = StorageInfo()

        db_path = self._backend.connection_config.database

        if db_path == ":memory:":
            storage.total_size_bytes = 0
            storage.extra["is_memory"] = True
        else:
            file_info = self._get_database_file_info(db_path)
            storage.total_size_bytes = file_info.get("size_bytes")
            storage.extra["path"] = db_path
            storage.extra["is_memory"] = False

        try:
            page_count = await self._pragma.get("page_count")
            if page_count and isinstance(page_count, dict):
                page_count = list(page_count.values())[0] if page_count else None

            page_size = await self._pragma.get("page_size")
            if page_size and isinstance(page_size, dict):
                page_size = list(page_size.values())[0] if page_size else None

            if page_count and page_size:
                calculated_size = int(page_count) * int(page_size)
                storage.data_size_bytes = calculated_size
                if storage.total_size_bytes is None:
                    storage.total_size_bytes = calculated_size
        except Exception:
            pass

        return storage

    async def list_databases(self) -> List[DatabaseBriefInfo]:
        """List attached databases.

        Returns:
            List of DatabaseBriefInfo objects
        """
        databases = []

        db_path = self._backend.connection_config.database
        main_db = DatabaseBriefInfo(
            name="main",
            schema=None,
            extra={"path": db_path, "is_memory": db_path == ":memory:"},
        )

        try:
            tables = await self._backend.introspector.list_tables(include_system=False)
            main_db.table_count = len(tables)
        except Exception:
            pass

        databases.append(main_db)

        try:
            pragma_databases = await self._pragma.execute("database_list")
            for row in pragma_databases:
                name = row.get("name")
                if name and name != "main":
                    db_info = DatabaseBriefInfo(
                        name=name,
                        schema=None,
                        extra={"path": row.get("file", "")},
                    )
                    databases.append(db_info)
        except Exception:
            pass

        return databases

    async def get_session_info(self) -> SessionInfo:
        """Get current session/connection information (empty for SQLite).

        Returns:
            Empty SessionInfo
        """
        return SessionInfo()
