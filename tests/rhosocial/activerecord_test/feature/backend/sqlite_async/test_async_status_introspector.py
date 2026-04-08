# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_status_introspector.py
"""
Tests for async SQLite status introspector.

This module tests the AsyncSQLiteStatusIntrospector functionality
for retrieving server status information via PRAGMA values.
"""

import os
import sqlite3

import pytest
import pytest_asyncio

from rhosocial.activerecord.backend.introspection.status import (
    StatusItem,
    StatusCategory,
    ServerOverview,
    DatabaseBriefInfo,
    UserInfo,
    ConnectionInfo,
    StorageInfo,
)
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend


class TestAsyncSQLiteStatusIntrospector:
    """Tests for asynchronous SQLite status introspector."""

    @pytest.mark.asyncio
    async def test_get_overview(self, async_sqlite_memory_backend):
        """Test get_overview returns valid ServerOverview."""
        status = async_sqlite_memory_backend.introspector.status

        overview = await status.get_overview()

        assert isinstance(overview, ServerOverview)
        assert overview.server_vendor == "SQLite"
        assert overview.server_version is not None
        assert isinstance(overview.configuration, list)
        assert isinstance(overview.performance, list)
        assert isinstance(overview.storage, StorageInfo)
        assert isinstance(overview.databases, list)
        assert overview.users == []  # SQLite has no users

    @pytest.mark.asyncio
    async def test_get_overview_version_matches_dialect(self, async_sqlite_memory_backend):
        """Test that overview version matches dialect version."""
        status = async_sqlite_memory_backend.introspector.status
        overview = await status.get_overview()

        expected_version = ".".join(map(str, async_sqlite_memory_backend.dialect.version))
        assert overview.server_version == expected_version

    @pytest.mark.asyncio
    async def test_get_overview_contains_sqlite_version_info(self, async_sqlite_memory_backend):
        """Test that overview contains SQLite version info in extra."""
        status = async_sqlite_memory_backend.introspector.status
        overview = await status.get_overview()

        assert "sqlite_version" in overview.extra
        assert overview.extra["sqlite_version"] == sqlite3.sqlite_version
        assert "sqlite_version_info" in overview.extra
        assert overview.extra["sqlite_version_info"] == sqlite3.sqlite_version_info

    @pytest.mark.asyncio
    async def test_list_configuration(self, async_sqlite_memory_backend):
        """Test list_configuration returns configuration items."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration()

        assert isinstance(items, list)
        assert len(items) > 0

        # Check that all items are StatusItem instances
        for item in items:
            assert isinstance(item, StatusItem)
            assert item.name is not None
            assert item.value is not None

    @pytest.mark.asyncio
    async def test_list_configuration_with_category_filter(self, async_sqlite_memory_backend):
        """Test list_configuration with category filter."""
        status = async_sqlite_memory_backend.introspector.status

        config_items = await status.list_configuration(category=StatusCategory.CONFIGURATION)

        for item in config_items:
            assert item.category == StatusCategory.CONFIGURATION

    @pytest.mark.asyncio
    async def test_list_configuration_contains_expected_items(self, async_sqlite_memory_backend):
        """Test that configuration contains expected PRAGMA items."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration()
        item_names = [item.name for item in items]

        # Check for some common PRAGMA values
        assert "journal_mode" in item_names
        assert "synchronous" in item_names
        assert "foreign_keys" in item_names

    @pytest.mark.asyncio
    async def test_list_configuration_values_are_parsed(self, async_sqlite_memory_backend):
        """Test that configuration values are properly parsed."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration()

        # cache_size should be an integer
        cache_size_item = next((i for i in items if i.name == "cache_size"), None)
        if cache_size_item:
            assert isinstance(cache_size_item.value, int)

    @pytest.mark.asyncio
    async def test_list_performance_metrics(self, async_sqlite_memory_backend):
        """Test list_performance_metrics returns performance items."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_performance_metrics()

        assert isinstance(items, list)

        # All items should be PERFORMANCE category
        for item in items:
            assert item.category == StatusCategory.PERFORMANCE

    @pytest.mark.asyncio
    async def test_get_connection_info(self, async_sqlite_memory_backend):
        """Test get_connection_info returns empty ConnectionInfo."""
        status = async_sqlite_memory_backend.introspector.status

        conn_info = await status.get_connection_info()

        assert isinstance(conn_info, ConnectionInfo)
        # SQLite has no connection concept, so should be empty

    @pytest.mark.asyncio
    async def test_get_storage_info_memory_database(self, async_sqlite_memory_backend):
        """Test get_storage_info for in-memory database."""
        status = async_sqlite_memory_backend.introspector.status

        storage = await status.get_storage_info()

        assert isinstance(storage, StorageInfo)
        assert storage.total_size_bytes == 0
        assert storage.extra.get("is_memory") is True

    @pytest.mark.asyncio
    async def test_get_storage_info_file_database(self, async_sqlite_backend):
        """Test get_storage_info for file-based database."""
        # Create some data to ensure file has content
        await async_sqlite_backend.executescript("""
            CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO test VALUES (1, 'test');
        """)

        status = async_sqlite_backend.introspector.status
        storage = await status.get_storage_info()

        assert isinstance(storage, StorageInfo)
        assert storage.extra.get("is_memory") is False
        assert "path" in storage.extra
        # File should have some size
        if storage.total_size_bytes is not None:
            assert storage.total_size_bytes >= 0

    @pytest.mark.asyncio
    async def test_get_storage_info_data_size(self, async_sqlite_backend):
        """Test get_storage_info calculates data size from pages."""
        await async_sqlite_backend.executescript("""
            CREATE TABLE test (id INTEGER PRIMARY KEY, name TEXT);
            INSERT INTO test VALUES (1, 'test');
        """)

        status = async_sqlite_backend.introspector.status
        storage = await status.get_storage_info()

        # data_size_bytes should be calculated from page_count * page_size
        if storage.data_size_bytes is not None:
            assert storage.data_size_bytes >= 0

    @pytest.mark.asyncio
    async def test_list_databases_main_only(self, async_sqlite_memory_backend):
        """Test list_databases returns main database."""
        status = async_sqlite_memory_backend.introspector.status

        databases = await status.list_databases()

        assert isinstance(databases, list)
        assert len(databases) >= 1

        main_db = databases[0]
        assert main_db.name == "main"
        assert main_db.extra.get("is_memory") is True

    @pytest.mark.asyncio
    async def test_list_databases_with_tables(self, async_backend_with_tables):
        """Test list_databases includes table count."""
        status = async_backend_with_tables.introspector.status

        databases = await status.list_databases()

        main_db = databases[0]
        assert main_db.table_count > 0

    @pytest.mark.asyncio
    async def test_list_databases_file_database(self, async_sqlite_backend):
        """Test list_databases for file-based database."""
        await async_sqlite_backend.executescript("""
            CREATE TABLE test (id INTEGER PRIMARY KEY);
        """)

        status = async_sqlite_backend.introspector.status
        databases = await status.list_databases()

        main_db = databases[0]
        assert main_db.name == "main"
        assert main_db.extra.get("is_memory") is False

    @pytest.mark.asyncio
    async def test_list_users(self, async_sqlite_memory_backend):
        """Test list_users returns empty list for SQLite."""
        status = async_sqlite_memory_backend.introspector.status

        users = await status.list_users()

        assert isinstance(users, list)
        assert len(users) == 0

    @pytest.mark.asyncio
    async def test_status_item_has_description(self, async_sqlite_memory_backend):
        """Test that status items have descriptions."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration()

        # Check that items have descriptions
        for item in items:
            assert item.description is not None

    @pytest.mark.asyncio
    async def test_status_item_readonly_flag(self, async_sqlite_memory_backend):
        """Test that readonly items are marked correctly."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration()

        # encoding should be readonly
        encoding_item = next((i for i in items if i.name == "encoding"), None)
        if encoding_item:
            assert encoding_item.is_readonly is True

        # journal_mode should not be readonly
        journal_item = next((i for i in items if i.name == "journal_mode"), None)
        if journal_item:
            assert journal_item.is_readonly is False


class TestAsyncSQLiteStatusIntrospectorMixin:
    """Tests for SQLiteStatusIntrospectorMixin helper methods."""

    @pytest.mark.asyncio
    async def test_parse_pragma_value_int(self, async_sqlite_memory_backend):
        """Test _parse_pragma_value handles integers."""
        status = async_sqlite_memory_backend.introspector.status

        result = status._parse_pragma_value(42)
        assert result == 42
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_parse_pragma_value_str_int(self, async_sqlite_memory_backend):
        """Test _parse_pragma_value parses string integers."""
        status = async_sqlite_memory_backend.introspector.status

        result = status._parse_pragma_value("42")
        assert result == 42
        assert isinstance(result, int)

    @pytest.mark.asyncio
    async def test_parse_pragma_value_str_non_int(self, async_sqlite_memory_backend):
        """Test _parse_pragma_value preserves non-integer strings."""
        status = async_sqlite_memory_backend.introspector.status

        result = status._parse_pragma_value("wal")
        assert result == "wal"
        assert isinstance(result, str)

    @pytest.mark.asyncio
    async def test_get_database_file_info_memory(self, async_sqlite_memory_backend):
        """Test _get_database_file_info for in-memory database."""
        status = async_sqlite_memory_backend.introspector.status

        info = status._get_database_file_info(":memory:")

        assert info["is_memory"] is True
        assert info["path"] == ":memory:"
        assert "size_bytes" not in info

    @pytest.mark.asyncio
    async def test_get_database_file_info_file(self, async_sqlite_backend):
        """Test _get_database_file_info for file database."""
        status = async_sqlite_backend.introspector.status
        db_path = async_sqlite_backend.config.database

        info = status._get_database_file_info(db_path)

        assert info["is_memory"] is False
        assert info["path"] == db_path
        assert "size_bytes" in info
        assert info["size_bytes"] >= 0

    @pytest.mark.asyncio
    async def test_create_status_item(self, async_sqlite_memory_backend):
        """Test _create_status_item creates proper StatusItem."""
        status = async_sqlite_memory_backend.introspector.status

        item = status._create_status_item(
            name="test_param",
            value="42",
            category=StatusCategory.CONFIGURATION,
            description="Test parameter",
            unit="ms",
            is_readonly=False,
        )

        assert isinstance(item, StatusItem)
        assert item.name == "test_param"
        assert item.value == 42  # Should be parsed to int
        assert item.category == StatusCategory.CONFIGURATION
        assert item.description == "Test parameter"
        assert item.unit == "ms"
        assert item.is_readonly is False

    @pytest.mark.asyncio
    async def test_get_vendor_name(self, async_sqlite_memory_backend):
        """Test _get_vendor_name returns SQLite."""
        status = async_sqlite_memory_backend.introspector.status

        vendor = status._get_vendor_name()
        assert vendor == "SQLite"


class TestAsyncStatusIntrospectorWithAttachedDatabase:
    """Tests for async status introspector with attached databases."""

    @pytest.mark.asyncio
    async def test_list_databases_with_attached(self, async_sqlite_backend):
        """Test list_databases includes attached databases."""
        import tempfile

        # Create a second database to attach
        fd, attach_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            await async_sqlite_backend.execute(
                f"ATTACH DATABASE '{attach_path}' AS attached_db",
                ()
            )

            status = async_sqlite_backend.introspector.status
            databases = await status.list_databases()

            # Should have at least main and attached_db
            db_names = [db.name for db in databases]
            assert "main" in db_names
            assert "attached_db" in db_names

        finally:
            if os.path.exists(attach_path):
                os.unlink(attach_path)


class TestAsyncStatusIntrospectorStorageCategories:
    """Tests for different status categories."""

    @pytest.mark.asyncio
    async def test_configuration_category_items(self, async_sqlite_memory_backend):
        """Test items in CONFIGURATION category."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.CONFIGURATION)

        for item in items:
            assert item.category == StatusCategory.CONFIGURATION

    @pytest.mark.asyncio
    async def test_performance_category_items(self, async_sqlite_memory_backend):
        """Test items in PERFORMANCE category."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.PERFORMANCE)

        for item in items:
            assert item.category == StatusCategory.PERFORMANCE

    @pytest.mark.asyncio
    async def test_storage_category_items(self, async_sqlite_memory_backend):
        """Test items in STORAGE category."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.STORAGE)

        for item in items:
            assert item.category == StatusCategory.STORAGE

    @pytest.mark.asyncio
    async def test_security_category_items(self, async_sqlite_memory_backend):
        """Test items in SECURITY category."""
        status = async_sqlite_memory_backend.introspector.status

        items = await status.list_configuration(category=StatusCategory.SECURITY)

        for item in items:
            assert item.category == StatusCategory.SECURITY
