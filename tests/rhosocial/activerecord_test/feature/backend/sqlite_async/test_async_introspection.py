# tests/rhosocial/activerecord_test/feature/backend/sqlite_async/test_async_introspection.py
"""
Tests for async SQLite introspection functionality.

This module tests the AsyncAbstractIntrospector implementation in SQLite,
including async database info, tables, columns, indexes, foreign keys,
views, and triggers introspection.
"""

import sqlite3

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    ForeignKeyInfo,
    ViewInfo,
    TriggerInfo,
    ColumnNullable,
)


class TestAsyncDatabaseIntrospection:
    """Tests for async database information introspection."""

    @pytest.mark.asyncio
    async def test_async_get_database_info(self, async_sqlite_backend):
        """Test async get_database_info returns valid DatabaseInfo."""
        db_info = await async_sqlite_backend.introspector.get_database_info()

        assert isinstance(db_info, DatabaseInfo)
        assert db_info.name == "main"
        assert db_info.vendor == "SQLite"
        assert db_info.version == sqlite3.sqlite_version
        assert db_info.version_tuple == sqlite3.sqlite_version_info

    @pytest.mark.asyncio
    async def test_async_database_info_version_tuple_format(self, async_sqlite_backend):
        """Test that version_tuple is correctly formatted."""
        db_info = await async_sqlite_backend.introspector.get_database_info()

        assert isinstance(db_info.version_tuple, tuple)
        assert len(db_info.version_tuple) == 3
        assert all(isinstance(x, int) for x in db_info.version_tuple)

    @pytest.mark.asyncio
    async def test_async_database_info_caching(self, async_sqlite_backend):
        """Test that database info is cached."""
        db_info1 = await async_sqlite_backend.introspector.get_database_info()
        db_info2 = await async_sqlite_backend.introspector.get_database_info()

        assert db_info1 is db_info2

    @pytest.mark.asyncio
    async def test_async_database_info_cache_invalidation(self, async_sqlite_backend):
        """Test that cache can be invalidated."""
        db_info1 = await async_sqlite_backend.introspector.get_database_info()

        async_sqlite_backend.introspector.clear_cache()

        db_info2 = await async_sqlite_backend.introspector.get_database_info()

        assert db_info1 is not db_info2
        assert db_info1.version == db_info2.version


class TestAsyncTableIntrospection:
    """Tests for async table introspection."""

    @pytest.mark.asyncio
    async def test_async_list_tables(self, async_backend_with_tables):
        """Test async list_tables returns all tables."""
        tables = await async_backend_with_tables.introspector.list_tables()

        assert isinstance(tables, list)
        assert len(tables) >= 4

        table_names = [t.name for t in tables]
        assert "users" in table_names
        assert "posts" in table_names
        assert "tags" in table_names

    @pytest.mark.asyncio
    async def test_async_get_table_info(self, async_backend_with_tables):
        """Test async get_table_info returns complete table information."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert isinstance(table_info, TableInfo)
        assert table_info.name == "users"
        assert table_info.columns is not None
        assert len(table_info.columns) == 5

    @pytest.mark.asyncio
    async def test_async_get_table_info_nonexistent(self, async_sqlite_backend):
        """Test async get_table_info for nonexistent table returns None."""
        table_info = await async_sqlite_backend.introspector.get_table_info("nonexistent")

        assert table_info is None

    @pytest.mark.asyncio
    async def test_async_table_exists(self, async_backend_with_tables):
        """Test async table_exists returns correct boolean."""
        assert await async_backend_with_tables.introspector.table_exists("users") is True
        assert await async_backend_with_tables.introspector.table_exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_async_list_tables_exclude_system(self, async_backend_with_tables):
        """Test async list_tables can exclude system tables."""
        tables = await async_backend_with_tables.introspector.list_tables(include_system=False)

        for table in tables:
            assert not table.name.startswith("sqlite_")


class TestAsyncColumnIntrospection:
    """Tests for async column introspection."""

    @pytest.mark.asyncio
    async def test_async_list_columns(self, async_backend_with_tables):
        """Test async list_columns returns all columns."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        assert isinstance(columns, list)
        assert len(columns) == 5

        column_names = [c.name for c in columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names
        assert "age" in column_names
        assert "created_at" in column_names

    @pytest.mark.asyncio
    async def test_async_get_column_info(self, async_backend_with_tables):
        """Test async get_column_info returns specific column."""
        column = await async_backend_with_tables.introspector.get_column_info("users", "email")

        assert isinstance(column, ColumnInfo)
        assert column.name == "email"
        assert column.nullable == ColumnNullable.NOT_NULL

    @pytest.mark.asyncio
    async def test_async_column_exists(self, async_backend_with_tables):
        """Test async column_exists returns correct boolean."""
        assert await async_backend_with_tables.introspector.column_exists("users", "email") is True
        assert await async_backend_with_tables.introspector.column_exists("users", "nonexistent") is False

    @pytest.mark.asyncio
    async def test_async_column_primary_key(self, async_backend_with_tables):
        """Test that primary key column is correctly identified."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        id_column = next(c for c in columns if c.name == "id")
        assert id_column.is_primary_key is True


class TestAsyncIndexIntrospection:
    """Tests for async index introspection."""

    @pytest.mark.asyncio
    async def test_async_list_indexes(self, async_backend_with_tables):
        """Test async list_indexes returns all indexes."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        assert isinstance(indexes, list)
        assert len(indexes) >= 2

        index_names = [i.name for i in indexes]
        assert "idx_users_email" in index_names

    @pytest.mark.asyncio
    async def test_async_get_index_info(self, async_backend_with_tables):
        """Test async get_index_info returns specific index."""
        index = await async_backend_with_tables.introspector.get_index_info("users", "idx_users_email")

        assert isinstance(index, IndexInfo)
        assert index.name == "idx_users_email"
        column_names = [c.name for c in index.columns]
        assert "email" in column_names

    @pytest.mark.asyncio
    async def test_async_get_primary_key(self, async_backend_with_tables):
        """Test async get_primary_key returns primary key index."""
        pk = await async_backend_with_tables.introspector.get_primary_key("users")

        if pk is not None:
            assert isinstance(pk, IndexInfo)
            assert pk.is_primary is True
            column_names = [c.name for c in pk.columns]
            assert "id" in column_names
        else:
            indexes = await async_backend_with_tables.introspector.list_indexes("users")
            pk_index = next((i for i in indexes if i.is_primary), None)
            if pk_index:
                assert pk_index.is_primary is True


class TestAsyncForeignKeyIntrospection:
    """Tests for async foreign key introspection."""

    @pytest.mark.asyncio
    async def test_async_list_foreign_keys(self, async_backend_with_tables):
        """Test async list_foreign_keys returns all foreign keys."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        assert isinstance(fks, list)
        assert len(fks) == 1

        fk = fks[0]
        assert isinstance(fk, ForeignKeyInfo)
        assert fk.referenced_table == "users"
        assert "user_id" in fk.columns
        assert "id" in fk.referenced_columns

    @pytest.mark.asyncio
    async def test_async_list_foreign_keys_no_fks(self, async_backend_with_tables):
        """Test async list_foreign_keys for table without foreign keys."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("users")

        assert isinstance(fks, list)
        assert len(fks) == 0

    @pytest.mark.asyncio
    async def test_async_composite_foreign_keys(self, async_backend_with_tables):
        """Test foreign keys for table with composite foreign keys."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("post_tags")

        assert isinstance(fks, list)
        assert len(fks) == 2


class TestAsyncViewIntrospection:
    """Tests for async view introspection."""

    @pytest.mark.asyncio
    async def test_async_list_views(self, async_backend_with_view):
        """Test async list_views returns all views."""
        views = await async_backend_with_view.introspector.list_views()

        assert isinstance(views, list)
        assert len(views) >= 1

        view_names = [v.name for v in views]
        assert "user_posts_summary" in view_names

    @pytest.mark.asyncio
    async def test_async_get_view_info(self, async_backend_with_view):
        """Test async get_view_info returns view definition."""
        view = await async_backend_with_view.introspector.get_view_info("user_posts_summary")

        assert isinstance(view, ViewInfo)
        assert view.name == "user_posts_summary"
        assert view.definition is not None

    @pytest.mark.asyncio
    async def test_async_view_exists(self, async_backend_with_view):
        """Test async view_exists returns correct boolean."""
        assert await async_backend_with_view.introspector.view_exists("user_posts_summary") is True
        assert await async_backend_with_view.introspector.view_exists("nonexistent_view") is False


class TestAsyncTriggerIntrospection:
    """Tests for async trigger introspection."""

    @pytest.mark.asyncio
    async def test_async_list_triggers(self, async_backend_with_trigger):
        """Test async list_triggers returns all triggers."""
        triggers = await async_backend_with_trigger.introspector.list_triggers()

        assert isinstance(triggers, list)
        assert len(triggers) >= 1

        trigger_names = [t.name for t in triggers]
        assert "update_user_timestamp" in trigger_names

    @pytest.mark.asyncio
    async def test_async_list_triggers_for_table(self, async_backend_with_trigger):
        """Test async list_triggers filtered by table."""
        triggers = await async_backend_with_trigger.introspector.list_triggers(table_name="users")

        assert isinstance(triggers, list)
        assert len(triggers) >= 1

        for trigger in triggers:
            assert trigger.table_name == "users"

    @pytest.mark.asyncio
    async def test_async_get_trigger_info(self, async_backend_with_trigger):
        """Test async get_trigger_info returns trigger definition."""
        trigger = await async_backend_with_trigger.introspector.get_trigger_info("update_user_timestamp")

        assert isinstance(trigger, TriggerInfo)
        assert trigger.name == "update_user_timestamp"
        assert trigger.table_name == "users"
        assert trigger.definition is not None


class TestAsyncIntrospectionCache:
    """Tests for async introspection caching."""

    @pytest.mark.asyncio
    async def test_async_cache_hit(self, async_backend_with_tables):
        """Test that cache is used for repeated queries."""
        tables1 = await async_backend_with_tables.introspector.list_tables()
        tables2 = await async_backend_with_tables.introspector.list_tables()

        assert tables1 is tables2

    @pytest.mark.asyncio
    async def test_async_cache_invalidation_by_scope(self, async_backend_with_tables):
        """Test cache invalidation by scope."""
        from rhosocial.activerecord.backend.introspection.types import IntrospectionScope

        await async_backend_with_tables.introspector.list_tables()
        await async_backend_with_tables.introspector.list_columns("users")

        async_backend_with_tables.introspector.invalidate_cache(
            IntrospectionScope.TABLE
        )

    @pytest.mark.asyncio
    async def test_async_clear_cache(self, async_backend_with_tables):
        """Test that clear_cache clears all cached data."""
        await async_backend_with_tables.introspector.get_database_info()
        await async_backend_with_tables.introspector.list_tables()

        async_backend_with_tables.introspector.clear_cache()

        assert len(async_backend_with_tables.introspector._cache) == 0


class TestAsyncConcurrentIntrospection:
    """Tests for concurrent async introspection operations."""

    @pytest.mark.asyncio
    async def test_concurrent_introspection_calls(self, async_backend_with_tables):
        """Test that concurrent introspection calls work correctly."""
        import asyncio

        results = await asyncio.gather(
            async_backend_with_tables.introspector.get_database_info(),
            async_backend_with_tables.introspector.list_tables(),
            async_backend_with_tables.introspector.list_columns("users"),
            async_backend_with_tables.introspector.list_indexes("users"),
            async_backend_with_tables.introspector.list_views(),
        )

        assert isinstance(results[0], DatabaseInfo)
        assert isinstance(results[1], list)
        assert isinstance(results[2], list)
        assert isinstance(results[3], list)
        assert isinstance(results[4], list)

    @pytest.mark.asyncio
    async def test_concurrent_table_info_calls(self, async_backend_with_tables):
        """Test concurrent get_table_info calls for different tables."""
        import asyncio

        results = await asyncio.gather(
            async_backend_with_tables.introspector.get_table_info("users"),
            async_backend_with_tables.introspector.get_table_info("posts"),
            async_backend_with_tables.introspector.get_table_info("tags"),
        )

        assert all(r is not None for r in results)
        assert results[0].name == "users"
        assert results[1].name == "posts"
        assert results[2].name == "tags"
