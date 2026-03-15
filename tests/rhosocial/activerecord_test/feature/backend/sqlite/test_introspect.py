# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_introspect.py
"""Tests for SQLite backend introspection and adaptation."""
import sqlite3
import pytest
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend, AsyncSQLiteBackend


class TestSQLiteIntrospect:
    """Tests for SQLite sync backend introspection."""

    def test_introspect_and_adapt(self):
        """Test introspect_and_adapt method."""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        # Get version before introspection
        version_before = backend.dialect.version
        print(f"\nVersion before introspect: {version_before}")
        print(f"sqlite3.sqlite_version: {sqlite3.sqlite_version}")
        print(f"sqlite3.sqlite_version_info: {sqlite3.sqlite_version_info}")

        # Introspect and adapt
        backend.introspect_and_adapt()

        # Get version after introspection
        version_after = backend.dialect.version
        print(f"Version after introspect: {version_after}")

        # Version should match sqlite3.sqlite_version_info
        assert version_after == sqlite3.sqlite_version_info

        backend.disconnect()

    def test_version_matches_sqlite3(self):
        """Test that dialect version matches sqlite3 library version."""
        backend = SQLiteBackend(database=":memory:")
        backend.connect()

        print(f"\nDialect version: {backend.dialect.version}")
        print(f"sqlite3.sqlite_version: {sqlite3.sqlite_version}")
        print(f"sqlite3.sqlite_version_info: {sqlite3.sqlite_version_info}")

        # Get server version should match
        server_version = backend.get_server_version()
        print(f"Server version: {server_version}")

        assert server_version == sqlite3.sqlite_version_info

        backend.disconnect()

    def test_version_affects_feature_detection(self):
        """Test that version affects feature detection."""
        # Create backend and manually set dialect version to old version
        backend_old = SQLiteBackend(database=":memory:")
        backend_old._dialect.version = (3, 30, 0)
        print(f"\nOld backend version: {backend_old.dialect.version}")
        print(f"supports_generated_columns: {backend_old.dialect.supports_generated_columns()}")
        print(f"supports_returning_clause: {backend_old.dialect.supports_returning_clause()}")

        assert backend_old.dialect.supports_generated_columns() is False
        assert backend_old.dialect.supports_returning_clause() is False

        # Create backend and manually set dialect version to new version
        backend_new = SQLiteBackend(database=":memory:")
        backend_new._dialect.version = (3, 35, 0)
        print(f"\nNew backend version: {backend_new.dialect.version}")
        print(f"supports_generated_columns: {backend_new.dialect.supports_generated_columns()}")
        print(f"supports_returning_clause: {backend_new.dialect.supports_returning_clause()}")

        assert backend_new.dialect.supports_generated_columns() is True
        assert backend_new.dialect.supports_returning_clause() is True

    def test_auto_version_detection(self):
        """Test automatic version detection from actual SQLite library."""
        backend = SQLiteBackend(database=":memory:")

        # Before connect, version might be default
        print(f"\nVersion before connect: {backend.dialect.version}")

        backend.connect()

        # After introspection, version should match actual library
        backend.introspect_and_adapt()

        print(f"Version after introspection: {backend.dialect.version}")
        print(f"sqlite3.sqlite_version_info: {sqlite3.sqlite_version_info}")

        assert backend.dialect.version == sqlite3.sqlite_version_info

        backend.disconnect()


class TestAsyncSQLiteIntrospect:
    """Tests for SQLite async backend introspection."""

    @pytest.mark.asyncio
    async def test_introspect_and_adapt(self):
        """Test async introspect_and_adapt method."""
        backend = AsyncSQLiteBackend(database=":memory:")
        await backend.connect()

        import aiosqlite
        print(f"\naiosqlite.sqlite_version: {aiosqlite.sqlite_version}")
        print(f"sqlite3.sqlite_version: {sqlite3.sqlite_version}")

        # Get version before introspection
        version_before = backend.dialect.version
        print(f"Version before introspect: {version_before}")

        # Introspect and adapt (currently empty implementation)
        await backend.introspect_and_adapt()

        # Get version after introspection
        version_after = backend.dialect.version
        print(f"Version after introspect: {version_after}")

        # Get server version
        server_version = backend.get_server_version()
        print(f"Server version: {server_version}")

        await backend.disconnect()

    @pytest.mark.asyncio
    async def test_version_comparison(self):
        """Compare version detection methods."""
        backend = AsyncSQLiteBackend(database=":memory:")

        print(f"\nDialect version (before connect): {backend.dialect.version}")

        await backend.connect()

        import aiosqlite
        print(f"aiosqlite.sqlite_version: {aiosqlite.sqlite_version}")
        print(f"sqlite3.sqlite_version_info: {sqlite3.sqlite_version_info}")

        server_version = backend.get_server_version()
        print(f"Server version: {server_version}")

        # Server version should match aiosqlite version
        version_str = aiosqlite.sqlite_version
        parts = version_str.split('.')
        expected_version = tuple(int(p) for p in parts[:3])
        while len(expected_version) < 3:
            expected_version = expected_version + (0,)

        assert server_version == expected_version

        await backend.disconnect()
