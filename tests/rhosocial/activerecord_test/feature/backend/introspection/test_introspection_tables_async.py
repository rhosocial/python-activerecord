# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_tables_async.py
"""Async twin of test_introspection_tables.py for SQLite table introspection."""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    TableInfo,
    TableType,
)


class TestAsyncListTables:
    """Tests for list_tables method."""

    @pytest.mark.asyncio
    async def test_list_tables_empty_database(self, async_sqlite_memory_backend):
        """Test list_tables on empty database."""
        tables = await async_sqlite_memory_backend.introspector.list_tables()
        assert isinstance(tables, list)
        assert len(tables) == 0

    @pytest.mark.asyncio
    async def test_list_tables_with_tables(self, async_backend_with_tables):
        """Test list_tables returns created tables."""
        tables = await async_backend_with_tables.introspector.list_tables()

        table_names = [t.name for t in tables]
        assert "users" in table_names
        assert "posts" in table_names
        assert "tags" in table_names
        assert "post_tags" in table_names

    @pytest.mark.asyncio
    async def test_list_tables_exclude_system_tables(self, async_backend_with_tables):
        """Test that system tables are excluded by default."""
        tables = await async_backend_with_tables.introspector.list_tables(include_system=False)

        table_names = [t.name for t in tables]
        for name in table_names:
            assert not name.startswith("sqlite_")

    @pytest.mark.asyncio
    async def test_list_tables_include_system_tables(self, async_sqlite_memory_backend):
        """Test that system tables can be included."""
        await async_sqlite_memory_backend.executescript(
            "CREATE TABLE test (id INTEGER PRIMARY KEY); CREATE INDEX idx_test ON test(id); ANALYZE;"
        )

        tables = await async_sqlite_memory_backend.introspector.list_tables(include_system=True)

        table_names = [t.name for t in tables]
        system_tables = [n for n in table_names if n.startswith("sqlite_")]
        assert len(system_tables) > 0

    @pytest.mark.asyncio
    async def test_list_tables_returns_table_info(self, async_backend_with_tables):
        """Test that list_tables returns TableInfo objects."""
        tables = await async_backend_with_tables.introspector.list_tables()

        for table in tables:
            assert isinstance(table, TableInfo)
            assert isinstance(table.table_type, TableType)
            assert table.schema == "main"

    @pytest.mark.asyncio
    async def test_list_tables_filter_by_type_base_table(self, async_backend_with_tables):
        """Test filtering tables by BASE TABLE type."""
        tables = await async_backend_with_tables.introspector.list_tables(table_type="BASE TABLE")

        for table in tables:
            assert table.table_type == TableType.BASE_TABLE

    @pytest.mark.asyncio
    async def test_list_tables_caching(self, async_backend_with_tables):
        """Test that table list is cached."""
        tables1 = await async_backend_with_tables.introspector.list_tables()
        tables2 = await async_backend_with_tables.introspector.list_tables()

        assert tables1 is tables2


class TestAsyncGetTableInfo:
    """Tests for get_table_info method."""

    @pytest.mark.asyncio
    async def test_get_table_info_existing_table(self, async_backend_with_tables):
        """Test get_table_info for existing table."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        assert isinstance(table_info, TableInfo)
        assert table_info.name == "users"
        assert table_info.schema == "main"
        assert table_info.table_type == TableType.BASE_TABLE

    @pytest.mark.asyncio
    async def test_get_table_info_nonexistent_table(self, async_sqlite_memory_backend):
        """Test get_table_info for non-existent table."""
        table_info = await async_sqlite_memory_backend.introspector.get_table_info("nonexistent")

        assert table_info is None

    @pytest.mark.asyncio
    async def test_get_table_info_includes_columns(self, async_backend_with_tables):
        """Test that get_table_info includes column information."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        assert len(table_info.columns) > 0

        column_names = [c.name for c in table_info.columns]
        assert "id" in column_names
        assert "name" in column_names
        assert "email" in column_names

    @pytest.mark.asyncio
    async def test_get_table_info_includes_indexes(self, async_backend_with_tables):
        """Test that get_table_info includes index information."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        assert len(table_info.indexes) > 0

        index_names = [i.name for i in table_info.indexes]
        assert "idx_users_email" in index_names

    @pytest.mark.asyncio
    async def test_get_table_info_includes_foreign_keys(self, async_backend_with_tables):
        """Test that get_table_info includes foreign key information."""
        table_info = await async_backend_with_tables.introspector.get_table_info("posts")

        assert table_info is not None
        assert len(table_info.foreign_keys) > 0

        fk = table_info.foreign_keys[0]
        assert fk.referenced_table == "users"

    @pytest.mark.asyncio
    async def test_get_table_info_caching(self, async_backend_with_tables):
        """Test that table info is cached."""
        info1 = await async_backend_with_tables.introspector.get_table_info("users")
        info2 = await async_backend_with_tables.introspector.get_table_info("users")

        assert info1 is info2


class TestAsyncTableExists:
    """Tests for table_exists method."""

    @pytest.mark.asyncio
    async def test_table_exists_true(self, async_backend_with_tables):
        """Test table_exists returns True for existing table."""
        assert await async_backend_with_tables.introspector.table_exists("users") is True
        assert await async_backend_with_tables.introspector.table_exists("posts") is True

    @pytest.mark.asyncio
    async def test_table_exists_false(self, async_sqlite_memory_backend):
        """Test table_exists returns False for non-existent table."""
        assert await async_sqlite_memory_backend.introspector.table_exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_table_exists_case_sensitive(self, async_backend_with_tables):
        """Test that table_exists is case-sensitive for stored names."""
        assert await async_backend_with_tables.introspector.table_exists("USERS") is False
        assert await async_backend_with_tables.introspector.table_exists("users") is True


class TestAsyncTableInfoDetails:
    """Tests for detailed table information."""

    @pytest.mark.asyncio
    async def test_column_ordinal_positions(self, async_backend_with_tables):
        """Test that column ordinal positions are correct."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        for i, col in enumerate(table_info.columns):
            assert col.ordinal_position == i + 1

    @pytest.mark.asyncio
    async def test_column_primary_key_detection(self, async_backend_with_tables):
        """Test that primary key columns are detected."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        id_col = next(c for c in table_info.columns if c.name == "id")
        assert id_col.is_primary_key is True

    @pytest.mark.asyncio
    async def test_column_not_null_detection(self, async_backend_with_tables):
        """Test that NOT NULL columns are detected."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        name_col = next(c for c in table_info.columns if c.name == "name")
        from rhosocial.activerecord.backend.introspection.types import ColumnNullable

        assert name_col.nullable == ColumnNullable.NOT_NULL

    @pytest.mark.asyncio
    async def test_column_nullable_detection(self, async_backend_with_tables):
        """Test that nullable columns are detected."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        age_col = next((c for c in table_info.columns if c.name == "age"), None)
        if age_col:
            from rhosocial.activerecord.backend.introspection.types import ColumnNullable

            assert age_col.nullable == ColumnNullable.NULLABLE

    @pytest.mark.asyncio
    async def test_column_default_value(self, async_backend_with_tables):
        """Test that default values are detected."""
        table_info = await async_backend_with_tables.introspector.get_table_info("users")

        assert table_info is not None
        created_at_col = next(c for c in table_info.columns if c.name == "created_at")
        assert created_at_col.default_value is not None

    @pytest.mark.asyncio
    async def test_composite_primary_key(self, async_sqlite_memory_backend):
        """Test detection of composite primary key."""
        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE composite_pk (
                col1 INTEGER NOT NULL,
                col2 INTEGER NOT NULL,
                data TEXT,
                PRIMARY KEY (col1, col2)
            );
        """)

        table_info = await async_sqlite_memory_backend.introspector.get_table_info("composite_pk")

        assert table_info is not None
        pk_columns = [c for c in table_info.columns if c.is_primary_key]
        assert len(pk_columns) == 2
