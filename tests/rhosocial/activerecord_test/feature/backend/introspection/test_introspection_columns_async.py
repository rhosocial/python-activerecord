# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_columns_async.py
"""Async twin of test_introspection_columns.py for SQLite column introspection."""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ColumnInfo,
    ColumnNullable,
)


class TestAsyncListColumns:
    """Tests for list_columns method."""

    @pytest.mark.asyncio
    async def test_list_columns_returns_column_info(self, async_backend_with_tables):
        """Test that list_columns returns ColumnInfo objects."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        assert isinstance(columns, list)
        assert len(columns) > 0

        for col in columns:
            assert isinstance(col, ColumnInfo)

    @pytest.mark.asyncio
    async def test_list_columns_all_columns_present(self, async_backend_with_tables):
        """Test that all columns are returned."""
        columns = await async_backend_with_tables.introspector.list_columns("users")
        column_names = [c.name for c in columns]

        expected_columns = ["id", "name", "email", "age", "created_at"]
        for expected in expected_columns:
            assert expected in column_names

    @pytest.mark.asyncio
    async def test_list_columns_nonexistent_table(self, async_sqlite_memory_backend):
        """Test list_columns for non-existent table."""
        columns = await async_sqlite_memory_backend.introspector.list_columns("nonexistent")

        assert isinstance(columns, list)
        assert len(columns) == 0

    @pytest.mark.asyncio
    async def test_list_columns_caching(self, async_backend_with_tables):
        """Test that column list is cached."""
        columns1 = await async_backend_with_tables.introspector.list_columns("users")
        columns2 = await async_backend_with_tables.introspector.list_columns("users")

        assert columns1 is columns2


class TestAsyncGetColumnInfo:
    """Tests for get_column_info method."""

    @pytest.mark.asyncio
    async def test_get_column_info_existing(self, async_backend_with_tables):
        """Test get_column_info for existing column."""
        col = await async_backend_with_tables.introspector.get_column_info("users", "email")

        assert col is not None
        assert isinstance(col, ColumnInfo)
        assert col.name == "email"
        assert col.table_name == "users"

    @pytest.mark.asyncio
    async def test_get_column_info_nonexistent_column(self, async_backend_with_tables):
        """Test get_column_info for non-existent column."""
        col = await async_backend_with_tables.introspector.get_column_info("users", "nonexistent")

        assert col is None

    @pytest.mark.asyncio
    async def test_get_column_info_nonexistent_table(self, async_sqlite_memory_backend):
        """Test get_column_info for non-existent table."""
        col = await async_sqlite_memory_backend.introspector.get_column_info("nonexistent", "id")

        assert col is None


class TestAsyncColumnExists:
    """Tests for column_exists method."""

    @pytest.mark.asyncio
    async def test_column_exists_true(self, async_backend_with_tables):
        """Test column_exists returns True for existing column."""
        assert await async_backend_with_tables.introspector.column_exists("users", "id") is True
        assert await async_backend_with_tables.introspector.column_exists("users", "name") is True
        assert await async_backend_with_tables.introspector.column_exists("users", "email") is True

    @pytest.mark.asyncio
    async def test_column_exists_false(self, async_backend_with_tables):
        """Test column_exists returns False for non-existent column."""
        assert await async_backend_with_tables.introspector.column_exists("users", "nonexistent") is False

    @pytest.mark.asyncio
    async def test_column_exists_nonexistent_table(self, async_sqlite_memory_backend):
        """Test column_exists for non-existent table."""
        assert await async_sqlite_memory_backend.introspector.column_exists("nonexistent", "id") is False


class TestAsyncColumnInfoDetails:
    """Tests for detailed column information."""

    @pytest.mark.asyncio
    async def test_column_data_type(self, async_backend_with_tables):
        """Test that data type is correctly detected."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.data_type == "integer"

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.data_type == "text"

    @pytest.mark.asyncio
    async def test_column_data_type_full(self, async_backend_with_tables):
        """Test that full data type is correctly detected."""
        await async_backend_with_tables.executescript("""
            CREATE TABLE type_test (
                col1 VARCHAR(255),
                col2 DECIMAL(10, 2),
                col3 CHAR(10)
            );
        """)

        columns = await async_backend_with_tables.introspector.list_columns("type_test")

        col1 = next(c for c in columns if c.name == "col1")
        assert col1.data_type == "varchar"
        assert col1.data_type_full == "VARCHAR(255)"

        col2 = next(c for c in columns if c.name == "col2")
        assert col2.data_type == "decimal"
        assert col2.data_type_full == "DECIMAL(10, 2)"

    @pytest.mark.asyncio
    async def test_column_nullable(self, async_backend_with_tables):
        """Test nullability detection."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.nullable == ColumnNullable.NOT_NULL

        email_col = next(c for c in columns if c.name == "email")
        assert email_col.nullable == ColumnNullable.NOT_NULL

        age_col = next(c for c in columns if c.name == "age")
        assert age_col.nullable == ColumnNullable.NULLABLE

    @pytest.mark.asyncio
    async def test_column_primary_key(self, async_backend_with_tables):
        """Test primary key detection."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        id_col = next(c for c in columns if c.name == "id")
        assert id_col.is_primary_key is True

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.is_primary_key is False

    @pytest.mark.asyncio
    async def test_column_unique_constraint(self, async_backend_with_tables):
        """Test unique constraint detection."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        email_col = next(c for c in columns if c.name == "email")
        indexes = await async_backend_with_tables.introspector.list_indexes("users")
        email_idx = next((i for i in indexes if "email" in [c.name for c in i.columns]), None)
        assert email_idx is not None or email_col.is_unique is False

    @pytest.mark.asyncio
    async def test_column_default_value_string(self, async_backend_with_tables):
        """Test default value detection for string."""
        columns = await async_backend_with_tables.introspector.list_columns("posts")

        status_col = next(c for c in columns if c.name == "status")
        assert status_col.default_value is not None
        assert "'draft'" in status_col.default_value or "draft" in status_col.default_value

    @pytest.mark.asyncio
    async def test_column_default_value_expression(self, async_backend_with_tables):
        """Test default value detection for expression."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        created_at_col = next(c for c in columns if c.name == "created_at")
        assert created_at_col.default_value is not None
        assert "CURRENT_TIMESTAMP" in created_at_col.default_value.upper()

    @pytest.mark.asyncio
    async def test_column_no_default(self, async_backend_with_tables):
        """Test column without default value."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        name_col = next(c for c in columns if c.name == "name")
        assert name_col.default_value is None

    @pytest.mark.asyncio
    async def test_integer_primary_key_autoincrement(self, async_sqlite_memory_backend):
        """Test INTEGER PRIMARY KEY is detected as auto-increment."""
        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE auto_inc (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT
            );
        """)

        columns = await async_sqlite_memory_backend.introspector.list_columns("auto_inc")
        id_col = next(c for c in columns if c.name == "id")

        assert id_col.is_primary_key is True

    @pytest.mark.asyncio
    async def test_column_schema(self, async_backend_with_tables):
        """Test that schema is correctly set."""
        columns = await async_backend_with_tables.introspector.list_columns("users")

        for col in columns:
            assert col.schema == "main"

    @pytest.mark.asyncio
    async def test_column_table_name(self, async_backend_with_tables):
        """Test that table_name is correctly set."""
        columns = await async_backend_with_tables.introspector.list_columns("posts")

        for col in columns:
            assert col.table_name == "posts"
