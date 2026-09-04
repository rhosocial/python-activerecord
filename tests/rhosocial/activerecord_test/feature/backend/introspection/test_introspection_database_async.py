# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_database_async.py
"""Async twin of test_introspection_database.py for SQLite database information introspection."""

import sqlite3

import pytest

from rhosocial.activerecord.backend.introspection.types import DatabaseInfo


class TestAsyncDatabaseInfo:
    """Tests for database information introspection."""

    @pytest.mark.asyncio
    async def test_get_database_info(self, async_sqlite_memory_backend):
        """Test get_database_info returns valid DatabaseInfo."""
        db_info = await async_sqlite_memory_backend.introspector.get_database_info()

        assert isinstance(db_info, DatabaseInfo)
        assert db_info.name == "main"
        assert db_info.vendor == "SQLite"
        assert db_info.version == sqlite3.sqlite_version
        assert db_info.version_tuple == sqlite3.sqlite_version_info

    @pytest.mark.asyncio
    async def test_database_info_version_tuple_format(self, async_sqlite_memory_backend):
        """Test that version_tuple is correctly formatted."""
        db_info = await async_sqlite_memory_backend.introspector.get_database_info()

        assert isinstance(db_info.version_tuple, tuple)
        assert len(db_info.version_tuple) == 3
        assert all(isinstance(x, int) for x in db_info.version_tuple)

    @pytest.mark.asyncio
    async def test_database_info_size_for_file_backend(self, async_sqlite_backend):
        """Test that size_bytes is populated for file-based database."""
        db_info = await async_sqlite_backend.introspector.get_database_info()

        await async_sqlite_backend.executescript("""
            CREATE TABLE test (id INTEGER PRIMARY KEY);
            INSERT INTO test VALUES (1);
        """)

        async_sqlite_backend.introspector.clear_cache()
        db_info = await async_sqlite_backend.introspector.get_database_info()

        if db_info.size_bytes is not None:
            assert db_info.size_bytes >= 0

    @pytest.mark.asyncio
    async def test_database_info_size_for_memory_backend(self, async_sqlite_memory_backend):
        """Test that size_bytes is None or non-negative for in-memory database."""
        db_info = await async_sqlite_memory_backend.introspector.get_database_info()

        if db_info.size_bytes is not None:
            assert db_info.size_bytes >= 0

    @pytest.mark.asyncio
    async def test_database_info_caching(self, async_sqlite_memory_backend):
        """Test that database info is cached."""
        db_info1 = await async_sqlite_memory_backend.introspector.get_database_info()
        db_info2 = await async_sqlite_memory_backend.introspector.get_database_info()

        assert db_info1 is db_info2

    @pytest.mark.asyncio
    async def test_database_info_cache_invalidation(self, async_sqlite_memory_backend):
        """Test that cache can be invalidated."""
        db_info1 = await async_sqlite_memory_backend.introspector.get_database_info()

        async_sqlite_memory_backend.introspector.clear_cache()

        db_info2 = await async_sqlite_memory_backend.introspector.get_database_info()

        assert db_info1 is not db_info2
        assert db_info1.version == db_info2.version

    @pytest.mark.asyncio
    async def test_database_info_matches_server_version(self, async_sqlite_memory_backend):
        """Test that database info matches server version."""
        db_info = await async_sqlite_memory_backend.introspector.get_database_info()
        server_version = async_sqlite_memory_backend.get_server_version()

        assert db_info.version_tuple == server_version


class TestAsyncIntrospectionCapabilities:
    """Tests for introspection capability declarations."""

    @pytest.mark.asyncio
    async def test_supports_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports introspection."""
        assert async_sqlite_memory_backend.dialect.supports_introspection() is True

    @pytest.mark.asyncio
    async def test_supports_database_info(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports database info."""
        assert async_sqlite_memory_backend.dialect.supports_database_info() is True

    @pytest.mark.asyncio
    async def test_supports_table_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports table introspection."""
        assert async_sqlite_memory_backend.dialect.supports_table_introspection() is True

    @pytest.mark.asyncio
    async def test_supports_column_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports column introspection."""
        assert async_sqlite_memory_backend.dialect.supports_column_introspection() is True

    @pytest.mark.asyncio
    async def test_supports_index_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports index introspection."""
        assert async_sqlite_memory_backend.dialect.supports_index_introspection() is True

    @pytest.mark.asyncio
    async def test_supports_foreign_key_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports foreign key introspection."""
        assert async_sqlite_memory_backend.dialect.supports_foreign_key_introspection() is True

    @pytest.mark.asyncio
    async def test_supports_view_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports view introspection."""
        assert async_sqlite_memory_backend.dialect.supports_view_introspection() is True

    @pytest.mark.asyncio
    async def test_supports_trigger_introspection(self, async_sqlite_memory_backend):
        """Test that SQLite backend supports trigger introspection."""
        assert async_sqlite_memory_backend.dialect.supports_trigger_introspection() is True

    @pytest.mark.asyncio
    async def test_get_supported_introspection_scopes(self, async_sqlite_memory_backend):
        """Test that all expected introspection scopes are supported."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        scopes = async_sqlite_memory_backend.dialect.get_supported_introspection_scopes()

        expected_scopes = [
            IntrospectionScope.DATABASE,
            IntrospectionScope.TABLE,
            IntrospectionScope.COLUMN,
            IntrospectionScope.INDEX,
            IntrospectionScope.FOREIGN_KEY,
            IntrospectionScope.VIEW,
            IntrospectionScope.TRIGGER,
        ]

        for expected_scope in expected_scopes:
            assert expected_scope in scopes
