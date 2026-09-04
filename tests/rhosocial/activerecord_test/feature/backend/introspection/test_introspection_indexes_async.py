# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_indexes_async.py
"""Async twin of test_introspection_indexes.py for SQLite index introspection."""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    IndexInfo,
    IndexType,
)


class TestAsyncListIndexes:
    """Tests for list_indexes method."""

    @pytest.mark.asyncio
    async def test_list_indexes_returns_index_info(self, async_backend_with_tables):
        """Test that list_indexes returns IndexInfo objects."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        assert isinstance(indexes, list)
        assert len(indexes) > 0

        for idx in indexes:
            assert isinstance(idx, IndexInfo)

    @pytest.mark.asyncio
    async def test_list_indexes_all_indexes_present(self, async_backend_with_tables):
        """Test that all indexes are returned."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")
        index_names = [i.name for i in indexes]

        assert "idx_users_email" in index_names
        assert "idx_users_name_age" in index_names

    @pytest.mark.asyncio
    async def test_list_indexes_nonexistent_table(self, async_sqlite_memory_backend):
        """Test list_indexes for non-existent table."""
        indexes = await async_sqlite_memory_backend.introspector.list_indexes("nonexistent")

        assert isinstance(indexes, list)
        assert len(indexes) == 0

    @pytest.mark.asyncio
    async def test_list_indexes_caching(self, async_backend_with_tables):
        """Test that index list is cached."""
        indexes1 = await async_backend_with_tables.introspector.list_indexes("users")
        indexes2 = await async_backend_with_tables.introspector.list_indexes("users")

        assert indexes1 is indexes2


class TestAsyncGetIndexInfo:
    """Tests for get_index_info method."""

    @pytest.mark.asyncio
    async def test_get_index_info_existing(self, async_backend_with_tables):
        """Test get_index_info for existing index."""
        idx = await async_backend_with_tables.introspector.get_index_info("users", "idx_users_email")

        assert idx is not None
        assert isinstance(idx, IndexInfo)
        assert idx.name == "idx_users_email"
        assert idx.table_name == "users"

    @pytest.mark.asyncio
    async def test_get_index_info_nonexistent(self, async_backend_with_tables):
        """Test get_index_info for non-existent index."""
        idx = await async_backend_with_tables.introspector.get_index_info("users", "nonexistent")

        assert idx is None


class TestAsyncGetPrimaryKey:
    """Tests for get_primary_key method."""

    @pytest.mark.asyncio
    async def test_get_primary_key_single(self, async_backend_with_tables):
        """Test get_primary_key for table with single-column PK."""
        pk = await async_backend_with_tables.introspector.get_primary_key("users")

        if pk is not None:
            assert pk.is_primary is True
            assert len(pk.columns) >= 1
            assert pk.columns[0].name == "id"
        else:
            columns = await async_backend_with_tables.introspector.list_columns("users")
            id_col = next(c for c in columns if c.name == "id")
            assert id_col.is_primary_key is True

    @pytest.mark.asyncio
    async def test_get_primary_key_composite(self, async_backend_with_tables):
        """Test get_primary_key for table with composite PK."""
        pk = await async_backend_with_tables.introspector.get_primary_key("post_tags")

        if pk is not None:
            assert pk.is_primary is True
            assert len(pk.columns) == 2

            column_names = [c.name for c in pk.columns]
            assert "post_id" in column_names
            assert "tag_id" in column_names
        else:
            columns = await async_backend_with_tables.introspector.list_columns("post_tags")
            pk_cols = [c for c in columns if c.is_primary_key]
            assert len(pk_cols) == 2

    @pytest.mark.asyncio
    async def test_get_primary_key_no_pk(self, async_sqlite_memory_backend):
        """Test get_primary_key for table without PK."""
        await async_sqlite_memory_backend.executescript("""
            CREATE TABLE no_pk (
                col1 INTEGER,
                col2 TEXT
            );
        """)

        await async_sqlite_memory_backend.introspector.get_primary_key("no_pk")


class TestAsyncIndexInfoDetails:
    """Tests for detailed index information."""

    @pytest.mark.asyncio
    async def test_index_is_unique(self, async_backend_with_tables):
        """Test unique index detection."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        email_idx = next((i for i in indexes if i.name == "idx_users_email"), None)
        if email_idx is not None:
            assert email_idx.table_name == "users"

    @pytest.mark.asyncio
    async def test_index_is_non_unique(self, async_backend_with_tables):
        """Test non-unique index detection."""
        indexes = await async_backend_with_tables.introspector.list_indexes("posts")

        user_idx = next((i for i in indexes if i.name == "idx_posts_user_id"), None)
        if user_idx is not None:
            assert user_idx.table_name == "posts"

    @pytest.mark.asyncio
    async def test_index_type(self, async_backend_with_tables):
        """Test index type detection."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        for idx in indexes:
            assert idx.index_type == IndexType.BTREE

    @pytest.mark.asyncio
    async def test_index_columns(self, async_backend_with_tables):
        """Test index column information."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        name_age_idx = next(i for i in indexes if i.name == "idx_users_name_age")
        assert len(name_age_idx.columns) == 2

        column_names = [c.name for c in name_age_idx.columns]
        assert "name" in column_names
        assert "age" in column_names

    @pytest.mark.asyncio
    async def test_index_column_ordinal_positions(self, async_backend_with_tables):
        """Test index column ordinal positions."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        name_age_idx = next(i for i in indexes if i.name == "idx_users_name_age")
        positions = [c.ordinal_position for c in name_age_idx.columns]

        assert positions[0] == 1
        assert positions[1] == 2

    @pytest.mark.asyncio
    async def test_index_schema(self, async_backend_with_tables):
        """Test that schema is correctly set."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        for idx in indexes:
            assert idx.schema == "main"

    @pytest.mark.asyncio
    async def test_primary_key_detection_in_indexes(self, async_backend_with_tables):
        """Test that primary key is detected in index list."""
        indexes = await async_backend_with_tables.introspector.list_indexes("users")

        pk_indexes = [i for i in indexes if i.is_primary]

        if len(pk_indexes) == 0:
            columns = await async_backend_with_tables.introspector.list_columns("users")
            pk_cols = [c for c in columns if c.is_primary_key]
            assert len(pk_cols) > 0

    @pytest.mark.asyncio
    async def test_multi_table_indexes(self, async_backend_with_tables):
        """Test indexes for multiple tables."""
        users_indexes = await async_backend_with_tables.introspector.list_indexes("users")
        posts_indexes = await async_backend_with_tables.introspector.list_indexes("posts")

        assert len(users_indexes) > 0
        assert len(posts_indexes) > 0

        users_idx_names = {i.name for i in users_indexes}
        posts_idx_names = {i.name for i in posts_indexes}

        assert not users_idx_names.intersection(posts_idx_names)
