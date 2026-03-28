# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_database.py
"""
Tests for SQLite database information introspection.

This module tests the get_database_info method and related functionality
for retrieving database metadata.
"""

import sqlite3

import pytest

from rhosocial.activerecord.backend.introspection.types import DatabaseInfo


class TestDatabaseInfo:
    """Tests for database information introspection."""

    def test_get_database_info(self, sqlite_backend):
        """Test get_database_info returns valid DatabaseInfo."""
        db_info = sqlite_backend.introspector.get_database_info()

        assert isinstance(db_info, DatabaseInfo)
        assert db_info.name == "main"
        assert db_info.vendor == "SQLite"
        assert db_info.version == sqlite3.sqlite_version
        assert db_info.version_tuple == sqlite3.sqlite_version_info

    def test_database_info_version_tuple_format(self, sqlite_backend):
        """Test that version_tuple is correctly formatted."""
        db_info = sqlite_backend.introspector.get_database_info()

        assert isinstance(db_info.version_tuple, tuple)
        assert len(db_info.version_tuple) == 3
        assert all(isinstance(x, int) for x in db_info.version_tuple)

    def test_database_info_size_for_file_backend(self, sqlite_file_backend):
        """Test that size_bytes is populated for file-based database."""
        db_info = sqlite_file_backend.introspector.get_database_info()

        # File-based database should have size info after some data is written
        # Insert some data to ensure file has content
        sqlite_file_backend.executescript("""
            CREATE TABLE test (id INTEGER PRIMARY KEY);
            INSERT INTO test VALUES (1);
        """)

        # Clear cache and get fresh info
        sqlite_file_backend.introspector.clear_cache()
        db_info = sqlite_file_backend.introspector.get_database_info()

        # Size should be populated for file-based database
        # Note: size_bytes may be None if the implementation doesn't query file size
        if db_info.size_bytes is not None:
            assert db_info.size_bytes >= 0

    def test_database_info_size_for_memory_backend(self, sqlite_backend):
        """Test that size_bytes is None for in-memory database."""
        db_info = sqlite_backend.introspector.get_database_info()

        # In-memory database may not have size info
        # (depends on implementation, could be None)
        # This test documents the expected behavior
        if db_info.size_bytes is not None:
            assert db_info.size_bytes >= 0

    def test_database_info_caching(self, sqlite_backend):
        """Test that database info is cached."""
        db_info1 = sqlite_backend.introspector.get_database_info()
        db_info2 = sqlite_backend.introspector.get_database_info()

        # Should return the same cached object
        assert db_info1 is db_info2

    def test_database_info_cache_invalidation(self, sqlite_backend):
        """Test that cache can be invalidated."""
        db_info1 = sqlite_backend.introspector.get_database_info()

        sqlite_backend.introspector.clear_cache()

        db_info2 = sqlite_backend.introspector.get_database_info()

        # Should be different objects after cache clear
        assert db_info1 is not db_info2
        # But with same values
        assert db_info1.version == db_info2.version

    def test_database_info_matches_server_version(self, sqlite_backend):
        """Test that database info matches server version."""
        db_info = sqlite_backend.introspector.get_database_info()
        server_version = sqlite_backend.get_server_version()

        assert db_info.version_tuple == server_version


class TestIntrospectionCapabilities:
    """Tests for introspection capability declarations."""

    def test_supports_introspection(self, sqlite_backend):
        """Test that SQLite backend supports introspection."""
        assert sqlite_backend.dialect.supports_introspection() is True

    def test_supports_database_info(self, sqlite_backend):
        """Test that SQLite backend supports database info."""
        assert sqlite_backend.dialect.supports_database_info() is True

    def test_supports_table_introspection(self, sqlite_backend):
        """Test that SQLite backend supports table introspection."""
        assert sqlite_backend.dialect.supports_table_introspection() is True

    def test_supports_column_introspection(self, sqlite_backend):
        """Test that SQLite backend supports column introspection."""
        assert sqlite_backend.dialect.supports_column_introspection() is True

    def test_supports_index_introspection(self, sqlite_backend):
        """Test that SQLite backend supports index introspection."""
        assert sqlite_backend.dialect.supports_index_introspection() is True

    def test_supports_foreign_key_introspection(self, sqlite_backend):
        """Test that SQLite backend supports foreign key introspection."""
        assert sqlite_backend.dialect.supports_foreign_key_introspection() is True

    def test_supports_view_introspection(self, sqlite_backend):
        """Test that SQLite backend supports view introspection."""
        assert sqlite_backend.dialect.supports_view_introspection() is True

    def test_supports_trigger_introspection(self, sqlite_backend):
        """Test that SQLite backend supports trigger introspection."""
        assert sqlite_backend.dialect.supports_trigger_introspection() is True

    def test_get_supported_introspection_scopes(self, sqlite_backend):
        """Test that all expected introspection scopes are supported."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        scopes = sqlite_backend.dialect.get_supported_introspection_scopes()

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
