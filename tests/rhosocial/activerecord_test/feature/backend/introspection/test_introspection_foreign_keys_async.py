# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_foreign_keys_async.py
"""Async twin of test_introspection_foreign_keys.py for SQLite foreign key introspection."""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ForeignKeyInfo,
    ReferentialAction,
)


class TestAsyncListForeignKeys:
    """Tests for list_foreign_keys method."""

    @pytest.mark.asyncio
    async def test_list_foreign_keys_returns_fk_info(self, async_backend_with_tables):
        """Test that list_foreign_keys returns ForeignKeyInfo objects."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        assert isinstance(fks, list)
        assert len(fks) > 0

        for fk in fks:
            assert isinstance(fk, ForeignKeyInfo)

    @pytest.mark.asyncio
    async def test_list_foreign_keys_posts_table(self, async_backend_with_tables):
        """Test foreign keys on posts table."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        assert len(fks) >= 1

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert "user_id" in user_fk.columns

    @pytest.mark.asyncio
    async def test_list_foreign_keys_post_tags_table(self, async_backend_with_tables):
        """Test foreign keys on post_tags table (composite FKs)."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("post_tags")

        assert len(fks) == 2

        referenced_tables = {fk.referenced_table for fk in fks}
        assert "posts" in referenced_tables
        assert "tags" in referenced_tables

    @pytest.mark.asyncio
    async def test_list_foreign_keys_no_fks(self, async_backend_with_tables):
        """Test list_foreign_keys for table without foreign keys."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("users")

        assert isinstance(fks, list)
        assert len(fks) == 0

    @pytest.mark.asyncio
    async def test_list_foreign_keys_nonexistent_table(self, async_sqlite_memory_backend):
        """Test list_foreign_keys for non-existent table."""
        fks = await async_sqlite_memory_backend.introspector.list_foreign_keys("nonexistent")

        assert isinstance(fks, list)
        assert len(fks) == 0

    @pytest.mark.asyncio
    async def test_list_foreign_keys_caching(self, async_backend_with_tables):
        """Test that foreign key list is cached."""
        fks1 = await async_backend_with_tables.introspector.list_foreign_keys("posts")
        fks2 = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        assert fks1 is fks2


class TestAsyncGetForeignKeyInfo:
    """Tests for get_foreign_key_info method."""

    @pytest.mark.asyncio
    async def test_get_foreign_key_info_existing(self, async_backend_with_tables):
        """Test get_foreign_key_info for existing FK."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")
        assert len(fks) > 0

        fk_name = fks[0].name
        fk = await async_backend_with_tables.introspector.get_foreign_key_info("posts", fk_name)

        assert fk is not None
        assert isinstance(fk, ForeignKeyInfo)
        assert fk.name == fk_name

    @pytest.mark.asyncio
    async def test_get_foreign_key_info_nonexistent(self, async_backend_with_tables):
        """Test get_foreign_key_info for non-existent FK."""
        fk = await async_backend_with_tables.introspector.get_foreign_key_info("posts", "nonexistent")

        assert fk is None


class TestAsyncForeignKeyDetails:
    """Tests for detailed foreign key information."""

    @pytest.mark.asyncio
    async def test_foreign_key_referenced_table(self, async_backend_with_tables):
        """Test referenced table detection."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None

    @pytest.mark.asyncio
    async def test_foreign_key_referenced_columns(self, async_backend_with_tables):
        """Test referenced columns detection."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert len(user_fk.referenced_columns) == 1
        assert user_fk.referenced_columns[0] == "id"

    @pytest.mark.asyncio
    async def test_foreign_key_on_delete_cascade(self, async_backend_with_tables):
        """Test ON DELETE CASCADE detection."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert user_fk.on_delete == ReferentialAction.CASCADE

    @pytest.mark.asyncio
    async def test_foreign_key_on_delete_no_action(self, async_backend_with_tables):
        """Test ON DELETE NO ACTION detection."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        user_fk = next((fk for fk in fks if fk.referenced_table == "users"), None)
        assert user_fk is not None
        assert user_fk.on_update == ReferentialAction.NO_ACTION

    @pytest.mark.asyncio
    async def test_foreign_key_on_delete_default(self, async_backend_with_tables):
        """Test default ON DELETE action."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("post_tags")

        for fk in fks:
            assert hasattr(fk.on_delete, "value")
            assert fk.on_delete.value in ("CASCADE", "NO ACTION")

    @pytest.mark.asyncio
    async def test_foreign_key_schema(self, async_backend_with_tables):
        """Test that schema is correctly set."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        for fk in fks:
            assert fk.schema == "main"

    @pytest.mark.asyncio
    async def test_foreign_key_table_name(self, async_backend_with_tables):
        """Test that table_name is correctly set."""
        fks = await async_backend_with_tables.introspector.list_foreign_keys("posts")

        for fk in fks:
            assert fk.table_name == "posts"

    @pytest.mark.asyncio
    async def test_composite_foreign_key_columns(self, async_sqlite_memory_backend):
        """Test composite foreign key columns."""
        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE parent (
                col1 INTEGER NOT NULL,
                col2 INTEGER NOT NULL,
                PRIMARY KEY (col1, col2)
            );

            CREATE TABLE child (
                id INTEGER PRIMARY KEY,
                parent_col1 INTEGER NOT NULL,
                parent_col2 INTEGER NOT NULL,
                FOREIGN KEY (parent_col1, parent_col2)
                    REFERENCES parent(col1, col2)
            );
        """)

        fks = await async_sqlite_memory_backend.introspector.list_foreign_keys("child")

        assert len(fks) == 1
        fk = fks[0]

        assert len(fk.columns) == 2
        assert len(fk.referenced_columns) == 2

        assert fk.columns == ["parent_col1", "parent_col2"]
        assert fk.referenced_columns == ["col1", "col2"]


class TestAsyncForeignKeyEnforcement:
    """Tests related to foreign key enforcement."""

    @pytest.mark.asyncio
    async def test_foreign_keys_not_enforced_by_default(self, async_sqlite_memory_backend):
        """Test that foreign keys can be introspected even when not enforced."""
        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE ref_table (
                id INTEGER PRIMARY KEY
            );

            CREATE TABLE main_table (
                id INTEGER PRIMARY KEY,
                ref_id INTEGER,
                FOREIGN KEY (ref_id) REFERENCES ref_table(id)
            );
        """)

        fks = await async_sqlite_memory_backend.introspector.list_foreign_keys("main_table")

        assert len(fks) == 1
        assert fks[0].referenced_table == "ref_table"
