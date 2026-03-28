# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_pragma_introspector.py
"""
Tests for async SQLite PRAGMA introspector.

This module tests the AsyncPragmaIntrospector class which provides
asynchronous access to SQLite's PRAGMA interface.
"""

import sqlite3

import pytest


class TestAsyncPragmaIntrospectorBasic:
    """Tests for basic async PRAGMA operations."""

    @pytest.mark.asyncio
    async def test_async_pragma_get_journal_mode(self, async_sqlite_backend):
        """Test getting journal_mode PRAGMA asynchronously."""
        pragma = async_sqlite_backend.introspector.pragma
        result = await pragma.get("journal_mode")

        assert result is not None
        assert "journal_mode" in result
        assert result["journal_mode"].upper() in ("WAL", "DELETE", "TRUNCATE", "MEMORY")

    @pytest.mark.asyncio
    async def test_async_pragma_get_with_argument(self, async_backend_with_tables):
        """Test getting PRAGMA with argument asynchronously."""
        pragma = async_backend_with_tables.introspector.pragma
        result = await pragma.get("table_info", "'users'")

        assert result is not None

    @pytest.mark.asyncio
    async def test_async_pragma_set_value(self, async_sqlite_backend):
        """Test setting a PRAGMA value asynchronously."""
        pragma = async_sqlite_backend.introspector.pragma

        await pragma.set("cache_size", 5000)

        result = await pragma.get("cache_size")
        assert result is not None
        assert result["cache_size"] == 5000

    @pytest.mark.asyncio
    async def test_async_pragma_set_with_schema(self, async_sqlite_backend):
        """Test setting PRAGMA with schema prefix asynchronously."""
        pragma = async_sqlite_backend.introspector.pragma

        await pragma.set("cache_size", 2000, schema="main")

        result = await pragma.get("cache_size", schema="main")
        assert result is not None

    @pytest.mark.asyncio
    async def test_async_pragma_execute_returns_list(self, async_backend_with_tables):
        """Test async execute method returns list of dicts."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.execute("table_info", "'users'")

        assert isinstance(result, list)
        assert len(result) >= 3
        for row in result:
            assert isinstance(row, dict)


class TestAsyncPragmaIntrospectorTableInfo:
    """Tests for async table_info and table_xinfo PRAGMAs."""

    @pytest.mark.asyncio
    async def test_async_table_info(self, async_backend_with_tables):
        """Test async table_info returns column information."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.table_info("users")

        assert isinstance(result, list)
        assert len(result) == 5

        id_col = result[0]
        assert id_col["name"] == "id"
        assert id_col["pk"] == 1

    @pytest.mark.asyncio
    async def test_async_table_info_nonexistent_table(self, async_sqlite_backend):
        """Test async table_info for nonexistent table."""
        pragma = async_sqlite_backend.introspector.pragma

        result = await pragma.table_info("nonexistent_table")

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_async_table_xinfo(self, async_backend_with_tables):
        """Test async table_xinfo returns column information with hidden columns."""
        pragma = async_backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 26, 0):
            pytest.skip("table_xinfo requires SQLite 3.26.0+")

        result = await pragma.table_xinfo("users")

        assert isinstance(result, list)
        assert len(result) >= 5

        for col in result:
            assert "hidden" in col

    @pytest.mark.asyncio
    async def test_async_table_info_with_schema(self, async_backend_with_tables):
        """Test async table_info with schema parameter."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.table_info("users", schema="main")

        assert isinstance(result, list)
        assert len(result) == 5


class TestAsyncPragmaIntrospectorIndexInfo:
    """Tests for async index_list, index_info, and index_xinfo PRAGMAs."""

    @pytest.mark.asyncio
    async def test_async_index_list(self, async_backend_with_tables):
        """Test async index_list returns indexes for a table."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.index_list("users")

        assert isinstance(result, list)
        assert len(result) >= 2

        index_names = [idx["name"] for idx in result]
        assert "idx_users_email" in index_names

    @pytest.mark.asyncio
    async def test_async_index_info(self, async_backend_with_tables):
        """Test async index_info returns columns in an index."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.index_info("idx_users_email")

        assert isinstance(result, list)
        assert len(result) == 1
        assert result[0]["name"] == "email"

    @pytest.mark.asyncio
    async def test_async_index_info_composite(self, async_backend_with_tables):
        """Test async index_info for composite index."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.index_info("idx_users_name_age")

        assert isinstance(result, list)
        assert len(result) == 2

        column_names = [col["name"] for col in result]
        assert "name" in column_names
        assert "age" in column_names

    @pytest.mark.asyncio
    async def test_async_index_xinfo(self, async_backend_with_tables):
        """Test async index_xinfo returns extended index information."""
        pragma = async_backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 9, 0):
            pytest.skip("index_xinfo requires SQLite 3.9.0+")

        result = await pragma.index_xinfo("idx_users_email")

        assert isinstance(result, list)
        assert len(result) >= 1


class TestAsyncPragmaIntrospectorForeignKeyList:
    """Tests for async foreign_key_list PRAGMA."""

    @pytest.mark.asyncio
    async def test_async_foreign_key_list(self, async_backend_with_tables):
        """Test async foreign_key_list returns foreign key information."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.foreign_key_list("posts")

        assert isinstance(result, list)
        assert len(result) == 1

        fk = result[0]
        assert fk["table"] == "users"
        assert fk["from"] == "user_id"
        assert fk["to"] == "id"

    @pytest.mark.asyncio
    async def test_async_foreign_key_list_no_fks(self, async_backend_with_tables):
        """Test async foreign_key_list for table without foreign keys."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.foreign_key_list("users")

        assert isinstance(result, list)
        assert len(result) == 0


class TestAsyncPragmaIntrospectorTableList:
    """Tests for async table_list PRAGMA."""

    @pytest.mark.asyncio
    async def test_async_table_list(self, async_backend_with_tables):
        """Test async table_list returns all tables."""
        pragma = async_backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 37, 0):
            pytest.skip("table_list requires SQLite 3.37.0+")

        result = await pragma.table_list()

        assert isinstance(result, list)
        assert len(result) >= 4

        table_names = [t["name"] for t in result]
        assert "users" in table_names
        assert "posts" in table_names

    @pytest.mark.asyncio
    async def test_async_table_list_with_schema(self, async_backend_with_tables):
        """Test async table_list with schema parameter."""
        pragma = async_backend_with_tables.introspector.pragma

        if sqlite3.sqlite_version_info < (3, 37, 0):
            pytest.skip("table_list requires SQLite 3.37.0+")

        result = await pragma.table_list(schema="main")

        assert isinstance(result, list)


class TestAsyncPragmaIntrospectorMaintenance:
    """Tests for async maintenance PRAGMAs."""

    @pytest.mark.asyncio
    async def test_async_integrity_check(self, async_backend_with_tables):
        """Test async integrity_check returns ok for valid database."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.integrity_check()

        assert isinstance(result, list)
        assert "ok" in result

    @pytest.mark.asyncio
    async def test_async_integrity_check_with_schema(self, async_backend_with_tables):
        """Test async integrity_check with schema parameter."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.integrity_check(schema="main")

        assert isinstance(result, list)
        assert "ok" in result

    @pytest.mark.asyncio
    async def test_async_foreign_key_check(self, async_backend_with_tables):
        """Test async foreign_key_check returns empty for valid FKs."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.foreign_key_check()

        assert isinstance(result, list)
        assert len(result) == 0

    @pytest.mark.asyncio
    async def test_async_foreign_key_check_with_table(self, async_backend_with_tables):
        """Test async foreign_key_check for specific table."""
        pragma = async_backend_with_tables.introspector.pragma

        result = await pragma.foreign_key_check(table_name="posts")

        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_async_journal_mode(self, async_sqlite_backend):
        """Test async journal_mode returns current mode."""
        pragma = async_sqlite_backend.introspector.pragma

        result = await pragma.journal_mode()

        assert result is not None
        assert isinstance(result, str)
        assert result.upper() in ("WAL", "DELETE", "TRUNCATE", "MEMORY", "OFF")

    @pytest.mark.asyncio
    async def test_async_wal_checkpoint(self, async_sqlite_backend):
        """Test async wal_checkpoint executes successfully."""
        pragma = async_sqlite_backend.introspector.pragma

        await pragma.set("journal_mode", "WAL")

        result = await pragma.wal_checkpoint()

        if result is not None:
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_async_wal_checkpoint_modes(self, async_sqlite_backend):
        """Test async wal_checkpoint with different modes."""
        pragma = async_sqlite_backend.introspector.pragma

        await pragma.set("journal_mode", "WAL")

        for mode in ["PASSIVE", "FULL", "RESTART", "TRUNCATE"]:
            result = await pragma.wal_checkpoint(mode=mode)
            if result is not None:
                assert isinstance(result, dict)


class TestAsyncPragmaIntrospectorSchemaParameter:
    """Tests for schema parameter in async PRAGMA operations."""

    @pytest.mark.asyncio
    async def test_async_table_info_with_temp_schema(self, async_sqlite_backend):
        """Test async table_info with temp schema."""
        await async_sqlite_backend.executescript("""
            CREATE TEMP TABLE temp_table (
                id INTEGER PRIMARY KEY,
                name TEXT
            );
        """)

        pragma = async_sqlite_backend.introspector.pragma

        result = await pragma.table_info("temp_table", schema="temp")

        assert isinstance(result, list)
        assert len(result) == 2


class TestAsyncPragmaIntrospectorConcurrent:
    """Tests for concurrent PRAGMA operations."""

    @pytest.mark.asyncio
    async def test_concurrent_pragma_reads(self, async_backend_with_tables):
        """Test concurrent PRAGMA reads work correctly."""
        import asyncio

        pragma = async_backend_with_tables.introspector.pragma

        results = await asyncio.gather(
            pragma.get("journal_mode"),
            pragma.get("cache_size"),
            pragma.table_info("users"),
            pragma.index_list("users"),
        )

        assert results[0] is not None
        assert results[1] is not None
        assert isinstance(results[2], list)
        assert isinstance(results[3], list)
